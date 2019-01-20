import cv2
import numpy as np
import nn_models
import data_loading.image_loading as il
import nn_models.Models as models
import data_loading.data_loaders as loaders
import numpy.random
import torch, random
import torch.nn as nn 
import torch.optim as optim
from tqdm import tqdm as tqdm
import pickle
from datetime import datetime
import os
import string
import glob
import argparse
import torchvision.transforms as transforms
import matplotlib.pyplot as plt
def main():
    parser = argparse.ArgumentParser(description="Playground")
    parser.add_argument("--dataset_file", type=str, required=True, help="Dataset file to use")
    args = parser.parse_args()
    dataset = loaders.F1ImageDataset(args.dataset_file,(66,200))
    dataset.loadFiles()
    #dataset.loadPickles()
    flows, labels = dataset[len(dataset)-1]

    print(flows.shape)
    print(labels.shape)

    print(flows[0])
#    print(flows[24])

    print(labels)

    dataset.writePickles()

if __name__ == '__main__':
    main()
