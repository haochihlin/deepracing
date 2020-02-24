import comet_ml
import torch
import torch.nn as NN
import torch.utils.data as data_utils
import deepracing_models.data_loading.proto_datasets as PD
from tqdm import tqdm as tqdm
import deepracing_models.nn_models.LossFunctions as loss_functions
import deepracing_models.nn_models.Models
import numpy as np
import torch.optim as optim
from tqdm import tqdm as tqdm
import pickle
from datetime import datetime
import os
import string
import argparse
import torchvision.transforms as transforms
import yaml
import shutil
import skimage
import skimage.io
import deepracing.backend
import imageio
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time
import deepracing_models.math_utils.bezier
import socket
import json

#torch.backends.cudnn.enabled = False
def run_epoch(experiment, network, optimizer, trainLoader, gpu, params_loss, kinematic_loss, loss_weights, epoch_number, imsize=(66,200), timewise_weights=None, debug=False, use_tqdm=True):
    cum_loss = 0.0
    cum_param_loss = 0.0
    cum_position_loss = 0.0
    cum_velocity_loss = 0.0
    num_samples=0.0
    batch_size = trainLoader.batch_size
    if use_tqdm:
        t = tqdm(enumerate(trainLoader), total=len(trainLoader))
    else:
        t = enumerate(trainLoader)
    network.train()  # This is important to call before training!
    dataloaderlen = len(trainLoader)
    # loss_weights_torch = torch.tensor(loss_weights)
    # if use_float:
    #     loss_weights_torch = session_times_torch.loss_weights_torch()
    # else:
    #     loss_weights_torch = loss_weights_torch.double()
    # if gpu>=0:
    #     loss_weights_torch = loss_weights_torch.cuda(gpu)
    _, _, _, _, _, _, sample_session_times = trainLoader.dataset[0]
    s_torch = torch.linspace(0.0,1.0,steps=sample_session_times.shape[0]).unsqueeze(0).repeat(batch_size,1).double()
    if gpu>=0:
        s_torch = s_torch.cuda(gpu)
    bezier_order = network.params_per_dimension-1
    for (i, (image_torch, opt_flow_torch, positions_torch, quats_torch, linear_velocities_torch, angular_velocities_torch, session_times_torch) ) in t:
        if network.input_channels==5:
            image_torch = torch.cat((image_torch,opt_flow_torch),axis=2)
        if gpu>=0:
            image_torch = image_torch.cuda(gpu)
            positions_torch = positions_torch.cuda(gpu)
            session_times_torch = session_times_torch.cuda(gpu)
            linear_velocities_torch = linear_velocities_torch.cuda(gpu)
        predictions = network(image_torch)
        predictions_reshape = predictions.transpose(1,2)
        dt = session_times_torch[:,-1]-session_times_torch[:,0]
        current_batch_size=session_times_torch.shape[0]
        current_timesteps=session_times_torch.shape[1]

        s_torch_cur = (session_times_torch - session_times_torch[:,0,None])/dt[:,None]
        
        
        gt_points = positions_torch[:,:,[0,2]]
        gt_vels = linear_velocities_torch[:,:,[0,2]]
        Mpos, controlpoints_fit = deepracing_models.math_utils.bezier.bezierLsqfit(gt_points, bezier_order, t = s_torch_cur)
        fit_points = torch.matmul(Mpos, controlpoints_fit)

        Mvel, fit_vels = deepracing_models.math_utils.bezier.bezierDerivative(controlpoints_fit, t = s_torch_cur, order=1)
        fit_vels_scaled = fit_vels/dt[:,None,None]
        

        pred_points = torch.matmul(Mpos, predictions_reshape)
        _, pred_vels = deepracing_models.math_utils.bezier.bezierDerivative(predictions_reshape, t = s_torch_cur, order=1)
        pred_vels_scaled = pred_vels/dt[:,None,None]
        
        if debug:
            # fig = plt.figure()
            # images_np = image_torch[0].detach().cpu().numpy().copy()
            # num_images = images_np.shape[0]
            # print(num_images)
            # images_np_transpose = np.zeros((num_images, images_np.shape[2], images_np.shape[3], images_np.shape[1]), dtype=np.uint8)
            # ims = []
            # for i in range(num_images):
            #     images_np_transpose[i]=skimage.util.img_as_ubyte(images_np[i].transpose(1,2,0))
            #     im = plt.imshow(images_np_transpose[i], animated=True)
            #     ims.append([im])
            # ani = animation.ArtistAnimation(fig, ims, interval=250, blit=True, repeat_delay=2000)
            fig2 = plt.figure()


            gt_points_np = gt_points[0,:].detach().cpu().numpy().copy()
            fit_points_np = fit_points[0].cpu().numpy().copy()


            gt_vels_np = gt_vels[0].cpu().numpy().copy()
            fit_vels_np = fit_vels_scaled[0].cpu().numpy().copy()


            plt.plot(gt_points_np[:,0],gt_points_np[:,1],'r+')
            plt.plot(fit_points_np[:,0],fit_points_np[:,1],'b-')

            #plt.quiver(gt_points_np[:,0],gt_points_np[:,1], gt_vels_np[:,0], gt_vels_np[:,1], color='g')
            # xmin, xmax = np.min(gt_points_np[:,0]), np.max(gt_points_np[:,0])
            # deltax = xmax-xmin
            # zmin, zmax = np.min(gt_points_np[:,1]), np.max(gt_points_np[:,1])
            # deltaz = zmax-zmin
            # deltaratio = deltaz/deltax

            #plt.quiver(fit_points_np[:,0],fit_points_np[:,1], deltaratio*fit_vels_np[:,0], fit_vels_np[:,1], color='r')
            plt.quiver(gt_points_np[:,0],gt_points_np[:,1], gt_vels_np[:,0], gt_vels_np[:,1], color='g', angles='xy')

            velocity_err = kinematic_loss(fit_vels_scaled, gt_vels).item()
            print("\nMean velocity error: %f\n" % (velocity_err))
            print(session_times_torch)
            print(dt)
            print(s_torch_cur)
            
            plt.show()

        current_position_loss = kinematic_loss(pred_points, gt_points)
        current_velocity_loss = kinematic_loss(pred_vels_scaled, gt_vels)
        current_param_loss = params_loss(predictions_reshape,controlpoints_fit)
        loss = loss_weights[0]*current_param_loss + loss_weights[1]*current_position_loss + loss_weights[2]*current_velocity_loss
  
       # loss = loss_weights[0]*current_param_loss + loss_weights[1]*current_position_loss + loss_weights[2]*current_velocity_loss
        
        # Backward pass:
        optimizer.zero_grad()
        loss.backward() 
        # Weight and bias updates.
        optimizer.step()
        # logging information
        cum_loss += float(loss.item())
        cum_param_loss += float(current_param_loss.item())
        cum_position_loss += float(current_position_loss.item())
        cum_velocity_loss += float(current_velocity_loss.item())
        num_samples += 1.0
        if not debug:
            experiment.log_metric("cumulative_position_error", cum_position_loss/num_samples, step=(epoch_number-1)*dataloaderlen + i)
            experiment.log_metric("cumulative_velocity_error", cum_velocity_loss/num_samples, step=(epoch_number-1)*dataloaderlen + i)
        if use_tqdm:
            t.set_postfix({"cum_loss" : cum_loss/num_samples,"cum_param_loss" : cum_param_loss/num_samples,"cum_position_loss" : cum_position_loss/num_samples,"cum_velocity_loss" : cum_velocity_loss/num_samples})
def go():
    parser = argparse.ArgumentParser(description="Train AdmiralNet Pose Predictor")
    parser.add_argument("experiment_id", type=str,  required=True, help="Dataset Configuration file to load")
    parser.add_argument("epochstart", type=int, required=True,  help="Restart training from the given epoch number")

    parser.add_argument("--api_key",  type=int, default=None,  help="Override the context length specified in the config file")
    parser.add_argument("--tqdm", action="store_true",  help="Display tqdm progress bar on each epoch")
    parser.add_argument("--gpu", type=int, default=-1,  help="Select GPU to use")
    

    args = parser.parse_args()

    experiment_id = args.experiment_id
    config_file = args.model_config_file
    epochstart = args.epochstart
    api_key = args.api_key
    tqdm = args.tqdm
    api_key = args.api_key
    gpu = args.gpu
       
    

    num_epochs = config["num_epochs"]
    num_workers = config["num_workers"]
    use_float = config["use_float"]
    hidden_dim = config["hidden_dimension"]
    loss_reduction = config["loss_reduction"]
    num_recurrent_layers = config.get("num_recurrent_layers",1)
    config["hostname"] = socket.gethostname()
    
    
    print("Using config:\n%s" % (str(config)))
    net = deepracing_models.nn_models.Models.AdmiralNetCurvePredictor( context_length = context_length , input_channels=input_channels, hidden_dim = hidden_dim, num_recurrent_layers=num_recurrent_layers, params_per_dimension=bezier_order+1 ) 
    print("net:\n%s" % (str(net)))
    ppd = net.params_per_dimension
    numones = int(ppd/2)
    if weighted_loss:
        timewise_weights = torch.from_numpy( np.hstack( ( np.ones(numones), np.linspace(1,3, ppd - numones ) ) ) )
    else:
        timewise_weights = None
    params_loss = deepracing_models.nn_models.LossFunctions.SquaredLpNormLoss(time_reduction=loss_reduction)
    kinematic_loss = deepracing_models.nn_models.LossFunctions.SquaredLpNormLoss(time_reduction=loss_reduction)
    if use_float:
        print("casting stuff to float")
        net = net.float()
        params_loss = params_loss.float()
        kinematic_loss = kinematic_loss.float()
    else:
        print("casting stuff to double")
        net = net.double()
        params_loss = params_loss.double()
        kinematic_loss = kinematic_loss.float()
    if gpu>=0:
        print("moving stuff to GPU")
        net = net.cuda(gpu)
        params_loss = params_loss.cuda(gpu)
        kinematic_loss = kinematic_loss.cuda(gpu)
    optimizer = args.optimizer
    net.linear_rnn.flatten_parameters()
    


    config["optimizer"] = optimizer
    if optimizer=="Adam":
        optimizer = optim.Adam(net.parameters(), lr = learning_rate, betas=(0.9, 0.9))
    elif optimizer=="RMSprop":
        optimizer = optim.RMSprop(net.parameters(), lr = learning_rate, momentum = momentum)
    elif optimizer=="ASGD":
        optimizer = optim.ASGD(net.parameters(), lr = learning_rate)
    elif optimizer=="SGD":
        nesterov_ = momentum>0.0 and nesterov
        if nesterov_:
            dampening_=0.0
        else:
            dampening_=dampening
        optimizer = optim.SGD( net.parameters(), lr = learning_rate , momentum = momentum , dampening = dampening_ , nesterov = nesterov_ )
    else:
        raise ValueError("Uknown optimizer " + optimizer)

   
    
    
    
        
    if num_workers == 0:
        max_spare_txns = 50
    else:
        max_spare_txns = num_workers

    #image_wrapper = deepracing.backend.ImageFolderWrapper(os.path.dirname(image_db))
    
    dsets=[]
    use_optflow = net.input_channels==5
    dsetfolders = []
    for dataset in dataset_config["datasets"]:
        print("Parsing database config: %s" %(str(dataset)))
        root_folder = dataset["root_folder"]
        dsetfolders.append(root_folder)
        label_folder = os.path.join(root_folder,"pose_sequence_labels")
        image_folder = os.path.join(root_folder,"images")
        key_file = os.path.join(root_folder,"goodkeys.txt")
        apply_color_jitter = dataset.get("apply_color_jitter",False)
        erasing_probability = dataset.get("erasing_probability",0.0)
        label_wrapper = deepracing.backend.PoseSequenceLabelLMDBWrapper()
        label_wrapper.readDatabase(os.path.join(label_folder,"lmdb"), max_spare_txns=max_spare_txns )
        image_mapsize = float(np.prod(image_size)*3+12)*float(len(label_wrapper.getKeys()))*1.1

        image_wrapper = deepracing.backend.ImageLMDBWrapper(direct_caching=False)
        image_wrapper.readDatabase(os.path.join(image_folder,"image_lmdb"), max_spare_txns=max_spare_txns, mapsize=image_mapsize )


        curent_dset = PD.PoseSequenceDataset(image_wrapper, label_wrapper, key_file, context_length,\
                     image_size = image_size, return_optflow=use_optflow, apply_color_jitter=apply_color_jitter, erasing_probability=erasing_probability)
        dsets.append(curent_dset)
        print("\n")
    if len(dsets)==1:
        dset = dsets[0]
    else:
        dset = torch.utils.data.ConcatDataset(dsets)
    
    dataloader = data_utils.DataLoader(dset, batch_size=batch_size,
                        shuffle=True, num_workers=num_workers, pin_memory=gpu>=0)
    print("Dataloader of of length %d" %(len(dataloader)))
    netpostfix = "epoch_%d_params.pt"
    optimizerpostfix = "epoch_%d_optimizer.pt"
    
    main_dir = args.output_directory
    if not debug:
        experiment = comet_ml.Experiment(workspace="electric-turtle", project_name="deepracingbezierpredictor")
        output_directory = os.path.join(main_dir, experiment.get_key())
        if os.path.isdir(output_directory) :
            raise FileExistsError("%s already exists, this should not happen." %(output_directory) )
        os.makedirs(output_directory)
        experiment.log_parameters(config)
        experiment.log_parameters(dataset_config)
        dsetsjson = json.dumps(dataset_config, indent=1)
        experiment.log_parameter("datasets",dsetsjson)
        experiment.log_text(dsetsjson)
        experiment.add_tag("bezierpredictor")
        experiment_config = {"experiment_key": experiment.get_key()}
        yaml.dump(experiment_config, stream=open(os.path.join(output_directory,"experiment_config.yaml"),"w"), Dumper=yaml.SafeDumper)
        yaml.dump(dataset_config, stream=open(os.path.join(output_directory,"dataset_config.yaml"), "w"), Dumper = yaml.SafeDumper)
        yaml.dump(config, stream=open(os.path.join(output_directory,"model_config.yaml"), "w"), Dumper = yaml.SafeDumper)
        experiment.log_asset(os.path.join(output_directory,"dataset_config.yaml"),file_name="datasets.yaml")
        experiment.log_asset(os.path.join(output_directory,"experiment_config.yaml"),file_name="experiment_config.yaml")
        experiment.log_asset(os.path.join(output_directory,"model_config.yaml"),file_name="model_config.yaml")
    else:
        output_directory = os.path.join(main_dir, "debug")
        os.makedirs(output_directory, exist_ok=True)
    i = 0
    if debug:
        run_epoch(None, net, optimizer, dataloader, gpu, params_loss, kinematic_loss, loss_weights, 1, debug=debug, use_tqdm=args.tqdm )
    else:
        with experiment.train():
            while i < num_epochs:
                time.sleep(2.0)
                postfix = i + 1
                print("Running Epoch Number %d" %(postfix))
                #dset.clearReaders()
                try:
                    tick = time.time()
                    run_epoch(experiment, net, optimizer, dataloader, gpu, params_loss, kinematic_loss, loss_weights, postfix, debug=debug, use_tqdm=args.tqdm )
                    tock = time.time()
                    print("Finished epoch %d in %f seconds." % ( postfix , tock-tick ) )
                    experiment.log_epoch_end(postfix)
                except Exception as e:
                    if isinstance(e, FileExistsError):
                        print(e)
                        exit(-1)
                    print("Restarting epoch %d because %s"%(postfix, str(e)))
                    modelin = os.path.join(output_directory, netpostfix %(postfix-1))
                    optimizerin = os.path.join(output_directory,optimizerpostfix %(postfix-1))
                    net.load_state_dict(torch.load(modelin))
                    optimizer.load_state_dict(torch.load(optimizerin))
                    continue
                modelout = os.path.join(output_directory,netpostfix %(postfix))
                torch.save(net.state_dict(), modelout)
                with open(modelout,'rb') as modelfile:
                    experiment.log_asset(modelfile,file_name=netpostfix %(postfix))
                optimizerout = os.path.join(output_directory,optimizerpostfix %(postfix))
                torch.save(optimizer.state_dict(), optimizerout)
                with open(optimizerout,'rb') as optimizerfile:
                    experiment.log_asset(optimizerfile,file_name=optimizerpostfix %(postfix))
                i = i + 1
import logging
if __name__ == '__main__':
    logging.basicConfig()
    go()    
    