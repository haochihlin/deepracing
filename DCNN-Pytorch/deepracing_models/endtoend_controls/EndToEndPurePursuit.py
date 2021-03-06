import Image_pb2
import TimestampedImage_pb2
import ChannelOrder_pb2
import PacketMotionData_pb2
import TimestampedPacketMotionData_pb2
import cv2
import numpy as np
import argparse
import skimage
import skimage.io as io
import os
import time
from concurrent import futures
import logging
import argparse
import lmdb
import cv2
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
import bisect
import traceback
import sys
import queue
from deepracing.controls.PurePursuitControl import PurePursuitController as PPC
from deepracing.controls.PurePursuitControl import OraclePurePursuitController as OraclePPC
import deepracing_models.math_utils as mu
import torch
import torch.nn as NN
import torch.utils.data as data_utils

import deepracing_models.nn_models.LossFunctions as loss_functions
import deepracing_models.nn_models.Models
import yaml
import matplotlib.pyplot as plt

def pbImageToNpImage(im_pb : Image_pb2.Image):
    im = None
    if im_pb.channel_order == ChannelOrder_pb2.BGR:
        im = np.reshape(np.frombuffer(im_pb.image_data,dtype=np.uint8),np.array((im_pb.rows, im_pb.cols, 3)))
        im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    elif im_pb.channel_order == ChannelOrder_pb2.RGB:
        im = np.reshape(np.frombuffer(im_pb.image_data,dtype=np.uint8),np.array((im_pb.rows, im_pb.cols, 3)))
    elif im_pb.channel_order == ChannelOrder_pb2.GRAYSCALE:
        im = np.reshape(np.frombuffer(im_pb.image_data,dtype=np.uint8),np.array((im_pb.rows, im_pb.cols)))
    elif im_pb.channel_order == ChannelOrder_pb2.RGBA:
        im = np.reshape(np.frombuffer(im_pb.image_data,dtype=np.uint8),np.array((im_pb.rows, im_pb.cols, 4)))
    elif im_pb.channel_order == ChannelOrder_pb2.BGRA:
        im = np.reshape(np.frombuffer(im_pb.image_data,dtype=np.uint8),np.array((im_pb.rows, im_pb.cols, 4)))
        im = cv2.cvtColor(im, cv2.COLOR_BGRA2RGBA)
    else:
        raise ValueError("Unknown channel order: " + im_pb.channel_order)
    return im
class AdmiralNetPurePursuitController(PPC):
    def __init__(self, model_file, trackfile=None, forward_indices = 60,  address="127.0.0.1", port=50052, lookahead_gain = 0.5, L = 3.617, pgain=0.5, igain=0.0125, dgain=0.0125, plot=True, gpu=1):
        super(AdmiralNetPurePursuitController, self).__init__(address=address, port=port, lookahead_gain = lookahead_gain, L = L ,\
                                                    pgain=pgain, igain=igain, dgain=dgain, deltaT = 1.415)
        if trackfile is not None:
            t, x, xdot = deepracing.loadArmaFile(trackfile)
            self.x = np.vstack((x.copy().transpose(),np.ones(x.shape[0])))
            self.xdot = xdot.copy().transpose()
            self.t = t.copy()
        self.deltaT = deltaT
        self.gpu = gpu
        self.forward_indices = forward_indices
        self.image_thread = threading.Thread(target=self.imageThread, args=(address, port-1))
        self.image_sock = None
        config_file = os.path.join(os.path.dirname(model_file),"config.yaml")
        with open(config_file,'r') as f:
            config = yaml.load(f, Loader = yaml.SafeLoader)
        input_channels = config["input_channels"]
        context_length = config["context_length"]
        bezier_order = config.get("bezier_order",None)
        sequence_length = config.get("sequence_length",None)
        if bezier_order is not None:
            self.net = nn_models.Models.AdmiralNetCurvePredictor(context_length= context_length, input_channels=input_channels, params_per_dimension=bezier_order+1) 
        else:
            hidden_dimension = config["hidden_dimension"]
            self.net = nn_models.Models.AdmiralNetKinematicPredictor(hidden_dim= hidden_dimension, input_channels=input_channels, output_dimension=2, sequence_length=sequence_length, context_length = context_length)
        self.net.load_state_dict(torch.load(model_file,map_location=torch.device("cpu")))
        self.net = self.net.double()
        self.net = self.net.cuda(self.gpu)
        self.image_buffer = RB(self.net.context_length,dtype=(float,(3,66,200)))
        self.optflow_buffer = RB(self.net.context_length,dtype=(float,(2,66,200)))
        if isinstance(self.net,  nn_models.Models.AdmiralNetCurvePredictor):
            self.s_torch = torch.linspace(0,1,60).unsqueeze(0).double().cuda(gpu)
            self.bezierM = mu.bezierM(self.s_torch,self.net.params_per_dimension-1).double().cuda(gpu)
        self.plot = plot
        self.trajplot = None
        self.fig = None
        self.ax = None
    def start(self):
        super().start()
        self.image_thread.start()
        self.net.eval()
    def imageThread(self, address, port):
        try:
            if self.image_sock is not None:
                self.image_sock.close()
            self.image_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.image_sock.bind((address, port))
            cv2.namedWindow("imrcv")
            current_image = Image_pb2.Image()
            imgcurrgrey = None
            imgprevgrey = None
            while self.running:
                data, addr = self.image_sock.recvfrom(52811) # buffer size is 1024 bytes.
                #print("Got %d bytes"% (len(data)))
                current_image.ParseFromString(data)
                imrcv = pbImageToNpImage(current_image)[:,:,0:3]
                # rowstart = 32
                # rowend = 394
                imcrop = imrcv[:,:,:]
                imresize = deepracing.imutils.resizeImage(imcrop,(66,200))
                imgcurrgrey = cv2.cvtColor(imresize,cv2.COLOR_RGB2GRAY)
                self.image_buffer.append(imresize.transpose(2,0,1).astype(np.float64)/255.0)
                if imgprevgrey is not None:
                    self.optflow_buffer.append(cv2.calcOpticalFlowFarneback(imgprevgrey, imgcurrgrey, None, 0.5, 3, 15, 3, 5, 1.2, 0).astype(np.float64).transpose(2,0,1))
                imgprevgrey = imgcurrgrey
                cv2.imshow("imrcv",cv2.cvtColor(imrcv,cv2.COLOR_RGB2BGR))
                cv2.waitKey(1)
               # print("Got Some Image Data")
                #current_packet.ParseFromString(data)
               #self.current_motion_data = current_packet.udp_packet
        except Exception as e:
            print(e)
    def getTrajectory(self):
        if self.current_motion_data is None:
            return None, None, None
        # motion_data = self.current_motion_data.m_carMotionData[0]
        # current_pos, current_quat = deepracing.pose_utils.extractPose(self.current_motion_data)
        # deltazmat = np.eye(4)
        # deltazmat[2,3] = -self.L/2
        # current_transform = np.matmul(deepracing.pose_utils.toHomogenousTransform(current_pos, current_quat), deltazmat)
        # current_transform_inv = la.inv(current_transform)
        # x_local_augmented = np.matmul(current_transform_inv,self.x)
        # x_local = x_local_augmented[[0,2],:].transpose()
        # v_local_augmented = np.matmul(current_transform_inv[0:3,0:3],self.xdot)
        # v_local = v_local_augmented[[0,2],:].transpose()
        # distances = la.norm(x_local, axis=1)
        # closest_index = np.argmin(distances)
        # forward_idx = np.linspace(closest_index,closest_index+self.forward_indices,self.forward_indices+1).astype(np.int32)%len(distances)
        # v_local_forward = v_local[forward_idx]
        # x_local_forward = x_local[forward_idx]
        # t_forward = self.t[forward_idx]
        # deltaT = t_forward[-1]-t_forward[0]
        # if deltaT<0.1:
        #     return x_local_forward, v_local_forward, distances[forward_idx]
        # s = (t_forward - t_forward[0])/deltaT
        # x_spline = scipy.interpolate.make_interp_spline(s, x_local_forward)
        # s_samp = np.linspace(0.0,1.0,96)
        # x_samp = x_spline(s_samp)
        # v_samp = (1/deltaT)*x_spline(s_samp,nu=1)
        # t_samp = s_samp*deltaT + t_forward[0]
        if(self.net.input_channels==3):
            imtorch = torch.from_numpy(np.array(self.image_buffer).copy())
            if (not imtorch.shape[0] == self.net.context_length):
                return None, None, None
            inputtorch = imtorch
        else:
            imtorch = torch.from_numpy(np.array(self.image_buffer).copy())
            optflowtorch = torch.from_numpy(np.array(self.optflow_buffer).copy())
            if (not optflowtorch.shape[0] == self.net.context_length) or (not imtorch.shape[0] == self.net.context_length):
                return None, None, None
            inputtorch = torch.cat([imtorch,optflowtorch],dim=1)
        if isinstance(self.net,  nn_models.Models.AdmiralNetCurvePredictor):
            bezier_control_points = self.net(inputtorch.unsqueeze(0).cuda(self.gpu)).transpose(1,2)
            evalpoints = torch.matmul(self.bezierM, bezier_control_points)
            x_samp = evalpoints[0].cpu().detach().numpy()
            x_samp[:,0]*=1.125
            _, evalvel = mu.bezierDerivative(bezier_control_points,self.s_torch)
            v_samp = (0.925)*(1/self.deltaT)*(evalvel[0].cpu().detach().numpy())
        else:
            evalpoints =  self.net(inputtorch.unsqueeze(0).cuda(self.gpu))
            x_samp = evalpoints[0].cpu().detach().numpy()
            x_samp[:,0]*=1.125
            tsamp = np.linspace(0,self.deltaT,60)
            spline = scipy.interpolate.make_interp_spline(tsamp,x_samp)
            splineder = spline.derivative()
            v_samp = splineder(tsamp)
        #print(x_samp)
        distances_samp = la.norm(x_samp, axis=1)
        if self.plot:
            if self.trajplot is None:
                self.fig = plt.figure()
                self.ax = self.fig.add_subplot()
                self.trajplot, = self.ax.plot(-x_samp[:,0],x_samp[:,1], color='b')
                self.ax.set_xlim(-15,15)
                self.ax.set_ylim(0,125)
                plt.show(block=False)
            else:
                self.trajplot.set_xdata(-x_samp[:,0])
                self.trajplot.set_ydata(x_samp[:,1])
                self.fig.canvas.draw()
                self.fig.canvas.flush_events()
        x_samp[:,1]-=self.L/2
        return x_samp, v_samp, distances_samp
        