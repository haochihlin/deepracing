import argparse
import skimage
import skimage.io as io
import os
import time
from concurrent import futures
import logging
import argparse
import lmdb
import deepracing.backend
from numpy_ringbuffer import RingBuffer as RB
import yaml
import torch
import torchvision
import torchvision.transforms as tf
import deepracing.imutils
import scipy
import scipy.interpolate
import py_f1_interface
import deepracing.pose_utils
import deepracing
import threading
import numpy.linalg as la
import scipy.integrate as integrate
import socket
import scipy.spatial
import queue
from f1_datalogger_rospy.controls.pure_puresuit_control_ros import PurePursuitControllerROS as PPC
import deepracing_models.math_utils as mu
import torch
import torch.nn as NN
import torch.utils.data as data_utils
import matplotlib.pyplot as plt
from sensor_msgs.msg import Image, CompressedImage
from f1_datalogger_msgs.msg import PathRaw, ImageWithPath, BezierCurve as BCMessage
from geometry_msgs.msg import Vector3Stamped, Vector3, PointStamped, Point, PoseStamped, Pose, Quaternion
from nav_msgs.msg import Path
from std_msgs.msg import Float64, Header
import rclpy
from rclpy import Parameter
from rclpy.node import Node
from rclpy.time import Time
from rclpy.clock import Clock, ROSClock
import deepracing_models.nn_models.Models as M
from scipy.spatial.transform import Rotation as Rot
import cv_bridge, cv2, numpy as np
import timeit

from copy import deepcopy

def npTrajectoryToROS(trajectory : np.ndarray, velocities : np.ndarray, frame_id = "map"):
    rtn : Path = Path()
    rtn.header.frame_id = frame_id
    for i in range(trajectory.shape[0]):
        point = trajectory[i]
        forward = np.array((velocities[i,0],0.0,velocities[i,1]), dtype=np.float64)
        up = np.array((0.0,1.0,0.0), dtype=np.float64)
        left = np.cross(up,forward)
        left[2] = 0.0
        left = left / la.norm(left)
        trueup =  np.cross(forward,left)
        trueup = trueup / la.norm(trueup)

        posestamped : PoseStamped = PoseStamped()
        posestamped.header.frame_id = frame_id
        pose : Pose = Pose()
        pose.position.x = point[0]
        pose.position.z = point[1]
       # pose.position.y = 0
       # pose.position.z = 0
        r = Rot.from_dcm(np.vstack((left, trueup, forward)).transpose())
        quat = r.as_quat()
        pose.orientation = Quaternion()
        pose.orientation.x = quat[0]
        pose.orientation.y = quat[1]
        pose.orientation.z = quat[2]
        pose.orientation.w = quat[3]
        posestamped.pose = pose
        rtn.poses.append(posestamped)
    return rtn
class AdmiralNetBezierPurePursuitControllerROS(PPC):
    def __init__(self, trackfile=None, forward_indices : int = 60, lookahead_gain : float = 0.4, L : float= 3.617, pgain: float=0.5, igain : float=0.0125, dgain : float=0.0125, plot : bool =True, gpu : int=0, deltaT : float = 1.415):
        super(AdmiralNetBezierPurePursuitControllerROS, self).__init__(lookahead_gain = lookahead_gain, L = L ,\
                                                    pgain=pgain, igain=igain, dgain=dgain)
        trackfile = self.get_parameter_or("trackfile", trackfile)
        # if (trackfile is not None) and ( not trackfile.type_==Parameter.Type.NOT_SET  ):
        #     t, x, xdot = deepracing.loadArmaFile(trackfile)
        #     self.xgt = np.vstack((x.copy().transpose(),np.ones(x.shape[0])))
        #     self.xdotgt = xdot.copy().transpose()
        #     self.tgt = t.copy()    
        self.path_publisher = self.create_publisher(BCMessage, "/predicted_path", 1)
        model_file_param = self.get_parameter("model_file")
        if (model_file_param.type_==Parameter.Type.NOT_SET):
            raise ValueError("The parameter \"model_file\" must be set for this rosnode")
        model_file = model_file_param.get_parameter_value().string_value
        print("Using model file : " + str(model_file))
        config_file = os.path.join(os.path.dirname(model_file),"config.yaml")
        if not os.path.isfile(config_file):
            config_file = os.path.join(os.path.dirname(model_file),"model_config.yaml")
        if not os.path.isfile(config_file):
            raise FileNotFoundError("Either config.yaml or model_config.yaml must exist in the same directory as the model file")
        with open(config_file,'r') as f:
            config = yaml.load(f, Loader = yaml.SafeLoader)
        input_channels = config["input_channels"]
        context_length = config["context_length"]
        bezier_order = config.get("bezier_order",None)
        sequence_length = config.get("sequence_length",None)
        use_3dconv = config.get("use_3dconv",True)
        self.fix_first_point = config.get("fix_first_point",False)
        self.rosclock = ROSClock()
        self.cvbridge : cv_bridge.CvBridge = cv_bridge.CvBridge()
        self.bufferdtpub = self.create_publisher(Float64, "/buffer_dt", 1)
        #self.rosclock._set_ros_time_is_active(True)


        L_param : Parameter = self.get_parameter_or("wheelbase",Parameter("wheelbase", value=L))
        print("L_param: " + str(L_param.get_parameter_value()))

        pgain_param : Parameter = self.get_parameter_or("pgain",Parameter("pgain", value=pgain))
        print("pgain_param: " + str(pgain_param.get_parameter_value()))

        igain_param : Parameter = self.get_parameter_or("igain",Parameter("igain", value=igain))
        print("igain_param: " + str(igain_param.get_parameter_value()))

        dgain_param : Parameter = self.get_parameter_or("dgain",Parameter("dgain", value=dgain))
        print("dgain_param: " + str(dgain_param.get_parameter_value()))

        lookahead_gain_param : Parameter = self.get_parameter_or("lookahead_gain",Parameter("lookahead_gain", value=lookahead_gain))
        print("lookahead_gain_param: " + str(lookahead_gain_param.get_parameter_value()))

        plot_param : Parameter = self.get_parameter_or("plot",Parameter("plot", value=plot))
        print("plot_param: " + str(plot_param.get_parameter_value()))

        use_compressed_images_param : Parameter = self.get_parameter_or("use_compressed_images",Parameter("use_compressed_images", value=False))
        print("use_compressed_images_param: " + str(use_compressed_images_param.get_parameter_value()))

        deltaT_param : Parameter = self.get_parameter_or("deltaT",Parameter("deltaT", value=deltaT))
        print("deltaT_param: " + str(deltaT_param.get_parameter_value()))

        forward_indices_param : Parameter = self.get_parameter_or("forward_indices",Parameter("forward_indices", value=forward_indices))
        print("forward_indices_param: " + str(forward_indices_param.get_parameter_value()))

        x_scale_factor_param : Parameter = self.get_parameter_or("x_scale_factor",Parameter("x_scale_factor", value=1.0))
        print("xscale_factor_param: " + str(x_scale_factor_param.get_parameter_value()))

        z_offset_param : Parameter = self.get_parameter_or("z_offset",Parameter("z_offset", value=L/2.0))
        print("z_offset_param: " + str(z_offset_param.get_parameter_value()))

        gpu_param = self.get_parameter_or("gpu",Parameter("gpu", value=gpu))
        print("gpu_param: " + str(gpu_param.get_parameter_value()))

        
        velocity_scale_param : Parameter = self.get_parameter_or("velocity_scale_factor",Parameter("velocity_scale_factor", value=1.0))
        print("velocity_scale_param: " + str(velocity_scale_param.get_parameter_value()))
        
        num_sample_points_param : Parameter = self.get_parameter_or("num_sample_points",Parameter("num_sample_points", value=60))
        print("num_sample_points_param: " + str(num_sample_points_param.get_parameter_value()))

        self.pgain : float = pgain_param.get_parameter_value().double_value
        self.igain : float = igain_param.get_parameter_value().double_value
        self.dgain : float = dgain_param.get_parameter_value().double_value
        self.lookahead_gain : float = lookahead_gain_param.get_parameter_value().double_value
        self.L = L_param.get_parameter_value().double_value
        self.z_offset : float = z_offset_param.get_parameter_value().double_value
        self.gpu : int = gpu_param.get_parameter_value().integer_value
        self.xscale_factor : float = x_scale_factor_param.get_parameter_value().double_value
        self.plot : bool = plot_param.get_parameter_value().bool_value
        self.velocity_scale_factor : float = velocity_scale_param.get_parameter_value().double_value
        self.num_sample_points : int = num_sample_points_param.get_parameter_value().integer_value
        self.deltaT : float = deltaT_param.get_parameter_value().double_value
        self.forward_indices : int = forward_indices_param.get_parameter_value().integer_value
        
        
        self.net : NN.Module = M.AdmiralNetCurvePredictor(context_length= context_length, input_channels=input_channels, params_per_dimension=bezier_order+1-int(self.fix_first_point), use_3dconv=use_3dconv) 
        self.net.double()
        self.get_logger().info('Loading model file: %s' % (model_file) )
        self.net.load_state_dict(torch.load(model_file,map_location=torch.device("cpu")))
        self.get_logger().info('Loaded model file: %s' % (model_file) )
        self.get_logger().info('Moving model params to GPU %d' % (self.gpu,))
        self.net = self.net.cuda(gpu)
        self.net = self.net.eval()

        self.get_logger().info('Moved model params to GPU %d' % (self.gpu,))
        self.image_buffer = RB(self.net.context_length,dtype=(float,(3,66,200)))
        self.s_torch = torch.linspace(0,1,self.num_sample_points, requires_grad=False).unsqueeze(0).double().cuda(self.gpu)
        self.bezier_order = self.net.params_per_dimension-1+int(self.fix_first_point)
        self.bezierM = mu.bezierM(self.s_torch,self.bezier_order).double().cuda(self.gpu)
        self.bezierMderiv = mu.bezierM(self.s_torch,self.bezier_order-1)
        self.buffertimer = timeit.Timer(stmt=self.addToBuffer)
        if self.fix_first_point:
            self.initial_zeros = torch.zeros(1,1,2).double()
            if self.gpu>=0:
                self.initial_zeros = self.initial_zeros.cuda(self.gpu) 
        self.bezierM.requires_grad = False
        self.bezierMderiv.requires_grad = False
        if use_compressed_images_param.get_parameter_value().bool_value:
            self.image_sub = self.create_subscription( CompressedImage, '/f1_screencaps/cropped/compressed', self.compressedImageCallback, 10)
        else:
            self.image_sub = self.create_subscription( Image, '/f1_screencaps/cropped', self.imageCallback, 10)
    def addToBuffer(self, img_msg : CompressedImage):
        try:
            imnp = self.cvbridge.compressed_imgmsg_to_cv2(img_msg, desired_encoding="rgb8") 
        except:
            return
        if imnp.shape[0]<=0 or imnp.shape[1]<=0 or (not imnp.shape[2]==3) :
            return
        imnpdouble = tf.functional.to_tensor(deepracing.imutils.resizeImage( imnp, (66,200) ) ).double().numpy().copy()
        self.image_buffer.append(imnpdouble)
    def compressedImageCallback(self, img_msg : CompressedImage):
        #t1 = timeit.default_timer()
        self.addToBuffer(img_msg)
        #t2 = timeit.default_timer()
        #self.bufferdtpub.publish(Float64(data=(t2-t1)))
    def imageCallback(self, img_msg : Image):
        if img_msg.height<=0 or img_msg.width<=0:
            return
        imnp = self.cvbridge.imgmsg_to_cv2(img_msg, desired_encoding="rgb8") 
        imnpdouble = tf.functional.to_tensor(deepracing.imutils.resizeImage( imnp, (66,200) ) ).double().numpy().copy()
        self.image_buffer.append(imnpdouble)
    def getTrajectory(self):
        if self.current_motion_data.world_velocity.header.frame_id == "":
            return None, None, None
        stamp = self.rosclock.now().to_msg()
        imnp = np.array(self.image_buffer).astype(np.float64).copy()
        imtorch = torch.from_numpy(imnp.copy())
        imtorch.required_grad = False
        if ( not imtorch.shape[0] == self.net.context_length ):
            return None, None, None
        inputtorch : torch.Tensor = imtorch.unsqueeze(0).double().cuda(self.gpu)
        self.get_logger().debug("inputtorch is on device %s" % (str(inputtorch.get_device())))
        with torch.no_grad():
            network_predictions = self.net(inputtorch)
            if self.fix_first_point:  
                bezier_control_points = torch.cat((self.initial_zeros,network_predictions.transpose(1,2)),dim=1)    
            else:
                bezier_control_points = network_predictions.transpose(1,2)
            evalpoints = torch.matmul(self.bezierM, bezier_control_points)
            x_samp = evalpoints[0].cpu().detach().numpy()
            x_samp[:,0]*=self.xscale_factor
            _, evalvel = mu.bezierDerivative(bezier_control_points, M = self.bezierMderiv)
            v_samp = self.velocity_scale_factor*(1.0/self.deltaT)*(evalvel[0].cpu().numpy())
        
        x_samp[:,1]-=self.z_offset
        #print(x_samp)
        distances_samp = la.norm(x_samp, axis=1)
        if self.plot:
            bezier_control_points_np = bezier_control_points[0].cpu().numpy()
            plotmsg : BCMessage = BCMessage(header = Header(stamp=stamp,frame_id="car"), control_points_x = bezier_control_points_np[:,0], control_points_z = bezier_control_points_np[:,1] )
            self.path_publisher.publish(plotmsg)
        return x_samp, v_samp, distances_samp
        