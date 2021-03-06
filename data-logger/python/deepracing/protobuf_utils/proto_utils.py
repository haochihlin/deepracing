import TimestampedPacketSessionData_pb2
import TimestampedPacketCarTelemetryData_pb2
import TimestampedPacketMotionData_pb2
import TimestampedPacketLapData_pb2
import TimestampedImage_pb2
import PacketMotionData_pb2
import CarTelemetryData_pb2
import Spline2DParams_pb2
import Vector3d_pb2
import Quaterniond_pb2
import os
import google.protobuf.json_format
import scipy.interpolate
import numpy as np
import numpy.linalg as la
from scipy.spatial.transform import Rotation as Rot
from tqdm import tqdm as tqdm
import BezierCurve_pb2

def splineSciPyToPB(splineSciPy : scipy.interpolate.BSpline, tmin,tmax,Xmin,Xmax,Zmin,Zmax):
   return Spline2DParams_pb2.Spline2DParams(XParams = splineSciPy.c[:,0], ZParams = splineSciPy.c[:,1],degree=splineSciPy.k, knots=splineSciPy.t,\
                                                           tmin=tmin,tmax=tmax,Xmin=Xmin,Xmax=Xmax,Zmin=Zmin,Zmax=Zmax)

def splinePBToSciPy(splinePB: Spline2DParams_pb2.Spline2DParams):
   return scipy.interpolate.BSpline(splinePB.knots, np.array([splinePB.XParams, splinePB.ZParams]).transpose(), splinePB.degree)
   
def getAllTelemetryPackets(telemetry_folder: str, use_json: bool):
   telemetry_packets = []
   if use_json:
      filepaths = [os.path.join(telemetry_folder, f) for f in os.listdir(telemetry_folder) if os.path.isfile(os.path.join(telemetry_folder, f)) and str.lower(os.path.splitext(f)[1])==".json"]
      jsonstrings = [(open(path, 'r')).read() for path in filepaths]
      for jsonstring in jsonstrings:
         data = TimestampedPacketCarTelemetryData_pb2.TimestampedPacketCarTelemetryData()
         google.protobuf.json_format.Parse(jsonstring, data)
         telemetry_packets.append(data)
   else:
      filepaths = [os.path.join(telemetry_folder, f) for f in os.listdir(telemetry_folder) if os.path.isfile(os.path.join(telemetry_folder, f)) and str.lower(os.path.splitext(f)[1])==".pb"]
      for filepath in filepaths:
         try:
            data = TimestampedPacketCarTelemetryData_pb2.TimestampedPacketCarTelemetryData()
            f = open(filepath,'rb')
            data.ParseFromString(f.read())
            f.close()
            telemetry_packets.append(data)
         except:
            f.close()
            print("Could not read telemetry packet file %s." %(filepath))
            continue
   return telemetry_packets
   
def getAllBezierCurves(bezier_curve_folder: str, use_json: bool):
   bezier_curves = []
   if use_json:
      filepaths = [os.path.join(bezier_curve_folder, f) for f in os.listdir(bezier_curve_folder) if os.path.isfile(os.path.join(bezier_curve_folder, f)) and os.path.splitext(f)[1].lower()==".json"]
      jsonstrings = [(open(path, 'r')).read() for path in filepaths]
      for jsonstring in jsonstrings:
         data = BezierCurve_pb2.BezierCurve()
         google.protobuf.json_format.Parse(jsonstring, data)
         bezier_curves.append(data)
   else:
      filepaths = [os.path.join(bezier_curve_folder, f) for f in os.listdir(bezier_curve_folder) if os.path.isfile(os.path.join(bezier_curve_folder, f)) and str.lower(os.path.splitext(f)[1])==".pb"]
      for filepath in filepaths:
         try:
            data = BezierCurve_pb2.BezierCurve()
            f = open(filepath,'rb')
            data.ParseFromString(f.read())
            f.close()
            bezier_curves.append(data)
         except:
            f.close()
            print("Could not read bezier curve binary file %s." %(filepath))
            continue
   return bezier_curves

def getAllSessionPackets(session_folder: str, use_json: bool):
   session_packets = []
   if use_json:
      filepaths = [os.path.join(session_folder, f) for f in os.listdir(session_folder) if os.path.isfile(os.path.join(session_folder, f)) and str.lower(os.path.splitext(f)[1])==".json"]
      jsonstrings = [(open(path, 'r')).read() for path in filepaths]
      for jsonstring in jsonstrings:
         data = TimestampedPacketSessionData_pb2.TimestampedPacketSessionData()
         google.protobuf.json_format.Parse(jsonstring, data)
         session_packets.append(data)
   else:
      filepaths = [os.path.join(session_folder, f) for f in os.listdir(session_folder) if os.path.isfile(os.path.join(session_folder, f)) and str.lower(os.path.splitext(f)[1])==".pb"]
      for filepath in filepaths:
         try:
            data = TimestampedPacketSessionData_pb2.TimestampedPacketSessionData()
            f = open(filepath,'rb')
            data.ParseFromString(f.read())
            f.close()
            session_packets.append(data)
         except:
            f.close()
            print("Could not read session packet file %s." %(filepath))
            continue
   return session_packets

def labelPacketToNumpy(label_tag):
   #print(label_tag.subsequent_poses)
   positions = np.array([np.array((pose.translation.x,pose.translation.y, pose.translation.z)) for pose in label_tag.subsequent_poses])
   quats = np.array([np.array((pose.rotation.x, pose.rotation.y, pose.rotation.z, pose.rotation.w)) for pose in label_tag.subsequent_poses])
   linear_velocities = np.array([np.array((vel.vector.x, vel.vector.y, vel.vector.z)) for vel in label_tag.subsequent_linear_velocities])
   angular_velocities = np.array([np.array((vel.vector.x, vel.vector.y, vel.vector.z)) for vel in label_tag.subsequent_angular_velocities])
   return positions, quats, linear_velocities, angular_velocities
def getAllLapDataPackets(lapdata_packet_folder: str, use_json: bool = False):
   lapdata_packets = []
   if use_json:
      filepaths = [os.path.join(lapdata_packet_folder, f) for f in os.listdir(lapdata_packet_folder) if os.path.isfile(os.path.join(lapdata_packet_folder, f)) and str.lower(os.path.splitext(f)[1])==".json"]
      jsonstrings = [(open(path, 'r')).read() for path in filepaths]
      for jsonstring in jsonstrings:
         data = TimestampedPacketLapData_pb2.TimestampedPacketLapData()
         google.protobuf.json_format.Parse(jsonstring, data)
         lapdata_packets.append(data)
   else:
      filepaths = [os.path.join(lapdata_packet_folder, f) for f in os.listdir(lapdata_packet_folder) if os.path.isfile(os.path.join(lapdata_packet_folder, f)) and str.lower(os.path.splitext(f)[1])==".pb"]
      for filepath in filepaths:
         try:
            data = TimestampedPacketLapData_pb2.TimestampedPacketLapData()
            f = open(filepath,'rb')
            data.ParseFromString(f.read())
            f.close()
            lapdata_packets.append(data)
         except Exception as e:
            f.close()
            print(str(e))
            print("Could not read binary file %s." %(filepath))
            continue
   return lapdata_packets
def getAllSequenceLabelPackets(label_packet_folder: str, use_json: bool = False):
   label_packets = []
   if use_json:
      filepaths = [os.path.join(label_packet_folder, f) for f in os.listdir(label_packet_folder) if os.path.isfile(os.path.join(label_packet_folder, f)) and str.lower(os.path.splitext(f)[1])==".json"]
      jsonstrings = [(open(path, 'r')).read() for path in filepaths]
      for jsonstring in jsonstrings:
         data = PoseSequenceLabel_pb2.PoseSequenceLabel()
         google.protobuf.json_format.Parse(jsonstring, data)
         label_packets.append(data)
   else:
      filepaths = [os.path.join(label_packet_folder, f) for f in os.listdir(label_packet_folder) if os.path.isfile(os.path.join(label_packet_folder, f)) and str.lower(os.path.splitext(f)[1])==".pb"]
      for filepath in filepaths:
         try:
            data = PoseSequenceLabel_pb2.PoseSequenceLabel()
            f = open(filepath,'rb')
            data.ParseFromString(f.read())
            f.close()
            label_packets.append(data)
         except Exception as e:
            f.close()
            print(str(e))
            print("Could not read binary file %s." %(filepath))
            continue
   return label_packets
def getAllMotionPackets(motion_data_folder: str, use_json: bool):
   motion_packets = []
   if use_json:
      filepaths = [os.path.join(motion_data_folder, f) for f in os.listdir(motion_data_folder) if os.path.isfile(os.path.join(motion_data_folder, f)) and str.lower(os.path.splitext(f)[1])==".json"]
      jsonstrings = [(open(path, 'r')).read() for path in filepaths]
      print("Loading json files for motion packets")
      for jsonstring in tqdm(jsonstrings):
         data = TimestampedPacketMotionData_pb2.TimestampedPacketMotionData()
         google.protobuf.json_format.Parse(jsonstring, data)
         motion_packets.append(data)
   else:
      filepaths = [os.path.join(motion_data_folder, f) for f in os.listdir(motion_data_folder) if os.path.isfile(os.path.join(motion_data_folder, f)) and str.lower(os.path.splitext(f)[1])==".pb"]
      print("Loading binary files for motion packets")
      for filepath in tqdm(filepaths):
         try:
            data = TimestampedPacketMotionData_pb2.TimestampedPacketMotionData()
            f = open(filepath,'rb')
            data.ParseFromString(f.read())
            f.close()
            motion_packets.append(data)
         except:
            f.close()
            print("Could not read udp file %s." %(filepath))
            continue
   return motion_packets
def getAllImageFilePackets(image_data_folder: str, use_json: bool):
   image_packets = []
   if use_json:
      filepaths = [os.path.join(image_data_folder, f) for f in os.listdir(image_data_folder) if os.path.isfile(os.path.join(image_data_folder, f)) and str.lower(os.path.splitext(f)[1])==".json"]
      jsonstrings = [(open(path, 'r')).read() for path in filepaths]
      for jsonstring in tqdm(jsonstrings):
         data = TimestampedImage_pb2.TimestampedImage()
         google.protobuf.json_format.Parse(jsonstring, data)
         image_packets.append(data)
   else:
      print("Attempting to read pb files in : %s" %(image_data_folder))
      filepaths = [os.path.join(image_data_folder, f) for f in os.listdir(image_data_folder) if os.path.isfile(os.path.join(image_data_folder, f)) and str.lower(os.path.splitext(f)[1])==".pb"]
      for filepath in tqdm(filepaths):
         try:
            data = TimestampedImage_pb2.TimestampedImage()
            f = open(filepath,'rb')
            data.ParseFromString(f.read())
            f.close()
            image_packets.append(data)
         except Exception as ex:
            #f.close()
            print("Could not read image data file %s." %(filepath))
            print(ex)
            continue
   return image_packets
def quaternionFromScipy(quaternion : Rot, quaternionpb = Quaterniond_pb2.Quaterniond()):
   return quaternionFromNumpy(quaternion.as_quat(), quaternionpb = quaternionpb)
def quaternionFromNumpy(quaternionnp : np.ndarray, quaternionpb = Quaterniond_pb2.Quaterniond()):
   quaternionpb.x = quaternionnp[0]
   quaternionpb.y = quaternionnp[1]
   quaternionpb.z = quaternionnp[2]
   quaternionpb.w = quaternionnp[3]
   return quaternionpb
def vectorFromNumpy(vectornp : np.ndarray, vectorpb =  Vector3d_pb2.Vector3d()):
   vectorpb.x = vectornp[0]
   vectorpb.y = vectornp[1]
   vectorpb.z = vectornp[2]
   return vectorpb


def extractAngularVelocity(packet):
    angular_velocity = np.array((packet.m_angularVelocityX, packet.m_angularVelocityY, packet.m_angularVelocityZ), np.float64)
    return angular_velocity
    
def extractVelocity(packet, car_index = None):
   if car_index is None:
      idx = packet.m_header.m_playerCarIndex
   else:
      idx = car_index
   motion_data = packet.m_carMotionData[idx]
   velocity = np.array((motion_data.m_worldVelocityX, motion_data.m_worldVelocityY, motion_data.m_worldVelocityZ), np.float64)
   return velocity
    
def extractPosition(packet , car_index = None):
   if car_index is None:
      idx = packet.m_header.m_playerCarIndex
   else:
      idx = car_index
   motion_data = packet.m_carMotionData[idx]
   position = np.array((motion_data.m_worldPositionX, motion_data.m_worldPositionY, motion_data.m_worldPositionZ), dtype=np.float64)
   return position 

def extractPose(packet : PacketMotionData_pb2.PacketMotionData, car_index = None):
   if car_index is None:
      idx = packet.m_header.m_playerCarIndex
   else:
      idx = car_index
   position = extractPosition(packet, car_index=idx)
   motion_data = packet.m_carMotionData[idx]
   rightvector = np.array((motion_data.m_worldRightDirX, motion_data.m_worldRightDirY, motion_data.m_worldRightDirZ), dtype=np.float64)
   rightvector = rightvector/la.norm(rightvector)
   forwardvector = np.array((motion_data.m_worldForwardDirX, motion_data.m_worldForwardDirY, motion_data.m_worldForwardDirZ), dtype=np.float64)
   forwardvector = forwardvector/la.norm(forwardvector)
   upvector = np.cross(rightvector,forwardvector)
   upvector = upvector/la.norm(upvector)
   rotationmat = np.column_stack((-rightvector,upvector,forwardvector))
   quat = Rot.from_matrix(rotationmat).as_quat()
   return position, quat 
def loadTrackfile(filepath : str):
   trackin = np.loadtxt(filepath,delimiter=",",skiprows=2)
   I = np.argsort(trackin[:,0])
   track = trackin[I].copy()
   r = track[:,0]
   X = np.zeros((track.shape[0],3))
   Xdot = np.zeros((track.shape[0],3))
   X[:,0] = track[:,1]
   X[:,1] = track[:,3]
   X[:,2] = track[:,2]

   

   return r, X