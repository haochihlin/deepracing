
import TimestampedPacketMotionData_pb2, TimestampedPacketCarTelemetryData_pb2
import argparse
import argcomplete
import os
import numpy as np
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
import matplotlib.pyplot as plt
import deepracing.protobuf_utils as proto_utils
import scipy
import scipy.spatial
import deepracing.evaluation_utils
import yaml
from matplotlib import pyplot as plt
import numpy.linalg as la
def analyzedatasets(main_dir,subdirs,prefix, results_dir="results", plot=False):
    mtbf= np.zeros(runmax)
    mdbf= np.zeros(runmax)
    mean_failure_scores = np.zeros(runmax)
    num_failures = np.zeros(runmax)
    results_dir = os.path.join(main_dir, results_dir, prefix)
    os.makedirs(results_dir,exist_ok=True)
    results_fp = os.path.join(results_dir, "results.yaml")
    resultsdict : dict = {}
    for (i, dset) in enumerate(subdirs):
        print("Running dataset %d for %s:"%(i+1, prefix), flush=True)
        dset_dir = os.path.join(main_dir, dset)
        motion_packets, failurescores, failuretimes, failuretimediffs, failuredistances, failuredistancediffs, velocities \
            = deepracing.evaluation_utils.evalDataset(dset_dir,\
            "../tracks/Australia_innerlimit.track", "../tracks/Australia_outerlimit.track", plot=plot)
        velocity_norms = 3.6*la.norm(velocities,axis=1)
        mtbf[i] = np.mean(failuretimediffs)
        mdbf[i] = np.mean(failuredistancediffs)
        mean_failure_scores[i] = np.mean(failurescores)
        num_failures[i] = float(failuredistances.shape[0])
        sessiontime_array = np.array([p.udp_packet.m_header.m_sessionTime for p in motion_packets])
        sessiontime_array = sessiontime_array - sessiontime_array[0]
       # fig = plt.figure()
        plt.plot(sessiontime_array, velocity_norms)
        plt.xlabel("Session Time")
        plt.ylabel("Velocity (kilometer/hour)")
        plt.title("Velocity Plot (Run %d)" %(i,))
        plt.savefig( os.path.join( results_dir, "velplot_run_%d.png" % (i,) ), bbox_inches='tight')
       # del fig
        # print( "Number of failures: %d" % ( num_failures[i] ) )
        # print( "Mean time between failures: %f" % ( mtbf[i] ) )
        # print( "Mean failure distance: %f" % ( mean_failure_distances[i] ) )
    resultsdict["mean_failure_scores"] = mean_failure_scores.tolist()
    resultsdict["num_failures"] = num_failures.tolist()
    resultsdict["mean_time_between_failures"] = mtbf.tolist()
    resultsdict["mean_distance_between_failures"] = mdbf.tolist()

    resultsdict["grandmean_failure_scores"] = np.mean(mean_failure_scores)
    resultsdict["grandmean_num_failures"] = np.mean(num_failures)
    resultsdict["grandmean_time_between_failures"] = np.mean(mtbf)
    resultsdict["grandmean_distance_between_failures"] = np.mean(mdbf)
    with open(results_fp,'w') as f:
        yaml.dump(resultsdict,f,Dumper=yaml.SafeDumper)

    print("\n", flush=True)
    print("Results for %s:"%(prefix))
    print( "Average Number of failures: %d" % ( np.mean(num_failures) ) , flush=True)
    print( "Overall Mean time between failures: %f" % ( np.mean(mtbf) ) , flush=True)
    print( "Overall Mean distance between failures: %f" % ( np.mean(mdbf) ) , flush=True)
    print( "Overall Mean failure score: %f" % (  np.mean(mean_failure_scores)  ) , flush=True)
    print("\n", flush=True)
parser = argparse.ArgumentParser()
parser.add_argument("main_dir", help="Directory of the evaluation datasets",  type=str)
args = parser.parse_args()
main_dir = args.main_dir

runmax = 5
bezier_dsets = ["bezier_predictor_run%d" % i for i in range(1,runmax+1)]
waypoint_dsets = ["waypoint_predictor_run%d" % i for i in range(1,runmax+1)]
cnnlstm_dsets = ["cnnlstm_run%d" % i for i in range(1,runmax+1)]
pilotnet_dsets = ["pilotnet_run%d" % i for i in range(1,runmax+1)]
print(bezier_dsets)
print(waypoint_dsets)
print(cnnlstm_dsets)
print(pilotnet_dsets)




analyzedatasets(main_dir,bezier_dsets,"Bezier_Predictor")
analyzedatasets(main_dir,waypoint_dsets,"Waypoint_Predictor")
analyzedatasets(main_dir,cnnlstm_dsets,"CNNLSTM")
analyzedatasets(main_dir,pilotnet_dsets,"PilotNet")

