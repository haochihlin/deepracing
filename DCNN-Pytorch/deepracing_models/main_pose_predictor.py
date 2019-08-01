import torch
import torch.utils.data as data_utils
import data_loading.proto_datasets
import data_loading.backend
from tqdm import tqdm as tqdm
import nn_models.LossFunctions as loss_functions
import nn_models.Models as models
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
loss = torch.zeros(1)
def run_epoch(network, optimizer, trainLoader, gpu, position_loss, rotation_loss, loss_weights=[1.0, 1.0], imsize=(66,200), debug=False):
    global loss
    cum_loss = 0.0
    cum_rotation_loss = 0.0
    cum_position_loss = 0.0
    batch_size = trainLoader.batch_size
    num_samples=0
    t = tqdm(enumerate(trainLoader))
    network.train()  # This is important to call before training!
    for (i, (image_torch, position_torch, rotation_torch, linear_velocity_torch, angular_velocity_torch, session_time)) in t:
        if debug:
            image_np = image_torch[0][0].numpy().copy()
            image_np = skimage.util.img_as_ubyte(image_np.transpose(1,2,0))
            skimage.io.imshow(image_np)
            skimage.io.show()
        if gpu>=0:
            image_torch = image_torch.cuda(gpu)
            position_torch = position_torch.cuda(gpu)
            rotation_torch = rotation_torch.cuda(gpu)
        images_nan = torch.sum(image_torch!=image_torch)!=0
        positions_labels_nan = torch.sum(position_torch!=position_torch)!=0
        rotation_labels_nan = torch.sum(rotation_torch!=rotation_torch)!=0
        if(images_nan):
            print(images_nan)
            raise ValueError("Input image block has a NaN!!!")
        if(rotation_labels_nan):
            print(rotation_torch)
            raise ValueError("Rotation label has a NaN!!!")
        if(positions_labels_nan):
            print(position_torch)
            raise ValueError("Position label has a NaN!!!")
      #  print(image_torch.dtype)
        # Forward pass:
        position_predictions, rotation_predictions = network(image_torch)
        positions_nan = torch.sum(position_predictions!=position_predictions)!=0
        rotation_nan = torch.sum(rotation_predictions!=rotation_predictions)!=0
        if(positions_nan):
            print(position_predictions)
            raise ValueError("Position prediction has a NaN!!!")
        if(rotation_nan):
            print(rotation_predictions)
            raise ValueError("Rotation prediction has a NaN!!!")
        #print("Output shape: ", outputs.shape)
        #print("Label shape: ", labels.shape)
        rotation_loss_ = rotation_loss(rotation_predictions, rotation_torch)
        rotation_loss_nan = torch.sum(rotation_loss_!=rotation_loss_)!=0
        if(rotation_loss_nan):
            print(rotation_loss_)
            raise ValueError("rotation_loss has a NaN!!!")
        position_loss_ = position_loss(position_predictions, position_torch)
        position_loss_nan = torch.sum(position_loss_!=position_loss_)!=0
        if(position_loss_nan):
            print(position_loss_)
            raise ValueError("position_loss has a NaN!!!")
        loss = loss_weights[0]*position_loss_ + loss_weights[1]*rotation_loss_
        loss_nan = torch.sum(loss!=loss)!=0
        if(positions_nan):
            print(loss)
            raise ValueError("loss has a NaN!!!")


        # Backward pass:
        optimizer.zero_grad()
        loss.backward() 

        # Weight and bias updates.
        optimizer.step()

        # logging information
        cum_loss += loss.item()
        cum_position_loss += position_loss_.item()
        cum_rotation_loss += rotation_loss_.item()
        num_samples += batch_size
        t.set_postfix({"cum_loss" : cum_loss/num_samples, "position_loss" : cum_position_loss/num_samples, "rotation_loss" : cum_rotation_loss/num_samples})
def go():
    parser = argparse.ArgumentParser(description="Train AdmiralNet Pose Predictor")
    parser.add_argument("config_file", type=str,  help="Configuration file to load")
    parser.add_argument("--debug", action="store_true",  help="Display images upon each iteration of the training loop")
    args = parser.parse_args()
    config_file = args.config_file
    debug = args.debug
    with open(config_file) as f:
        config = yaml.load(f, Loader = yaml.SafeLoader)
    annotation_dir = config["annotation_dir"]
    image_server_address = config["image_server_address"]
    image_server_port = config["image_server_port"]
    image_size = config["image_size"]
    hidden_dimension = config["hidden_dimension"]
    input_channels = config["input_channels"]
    sequence_length = config["sequence_length"]
    context_length = config["context_length"]
    gpu = config["gpu"]
    loss_weights = config["loss_weights"]
    temporal_conv_feature_factor = config["temporal_conv_feature_factor"]
    batch_size = config["batch_size"]
    learning_rate = config["learning_rate"]
    momentum = config["momentum"]
    num_epochs = config["num_epochs"]
    output_directory = config["output_directory"]
    num_workers = config["num_workers"]
    debug = config["debug"]
    if os.path.isdir(output_directory):
        s = ""
        while(not (s=="y" or s=="n")):
             s = input("Directory " + output_directory + " already exists. Overwrite it with new data? [y\\n]\n")
        if s=="n":
            print("Thanks for playing!")
            exit(0)
        shutil.rmtree(output_directory)
    os.makedirs(output_directory)
    net = models.AdmiralNetPosePredictor(gpu=gpu,context_length = context_length, sequence_length = sequence_length,\
        hidden_dim=hidden_dimension, input_channels=input_channels, temporal_conv_feature_factor = temporal_conv_feature_factor)
    position_loss = torch.nn.MSELoss(reduction='sum')
    rotation_loss = loss_functions.QuaternionDistance()
    optimizer = optim.SGD(net.parameters(), lr = learning_rate, momentum=momentum)
    if gpu>=0:
        rotation_loss = rotation_loss.cuda(gpu)
        position_loss = position_loss.cuda(gpu)
        net = net.cuda(gpu)
    db_wrapper = data_loading.backend.GRPCWrapper(address =image_server_address, port=image_server_port)
    dset = data_loading.proto_datasets.ProtoDirDataset(annotation_dir, db_wrapper, context_length, sequence_length, image_size = np.array(image_size))
    dataloader = data_utils.DataLoader(dset, batch_size=batch_size,
                            shuffle=True, num_workers=num_workers)
    yaml.dump(config, stream=open(os.path.join(output_directory,"config.yaml"), "w"), Dumper = yaml.SafeDumper)
    i = 0
    while i < num_epochs:
        postfix = i + 1
        print("Running Epoch Number %d" %(postfix))
        try:
            run_epoch(net, optimizer, dataloader, gpu, position_loss, rotation_loss, loss_weights=loss_weights, debug=debug)
        except Exception as e:
            print("Restarting epoch %d because %s"%(postfix, str(e)))
            modelin = os.path.join(output_directory,"epoch_%d_params.pt" %(postfix-1))
            optimizerin = os.path.join(output_directory,"epoch_%d_optimizer.pt" %(postfix-1))
            net.load_state_dict(torch.load(modelin))
            optimizer.load_state_dict(torch.load(optimizerin))
            continue
        modelout = os.path.join(output_directory,"epoch_%d_params.pt" %(postfix))
        torch.save(net.state_dict(), modelout)
        optimizerout = os.path.join(output_directory,"epoch_%d_optimizer.pt" %(postfix))
        torch.save(optimizer.state_dict(), optimizerout)
        irand = np.random.randint(0,high=len(dset))
        imtest = torch.rand( 1, context_length, input_channels, image_size[0], image_size[1], dtype=torch.float32 )
        imtest[0], positions_torch, quats_torch, _, _, _ = dset[irand]
        if(gpu>=0):
            imtest = imtest.cuda(gpu)
        pos_pred, rot_pred = net(imtest)
        print(positions_torch)
        print(pos_pred)
        print(quats_torch)
        print(rot_pred)
        i = i + 1
import logging
if __name__ == '__main__':
    logging.basicConfig()
    go()    
    