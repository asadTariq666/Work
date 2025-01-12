# Here is a code to load the data (CIFAR-10) from your hard drive.
# First load the CIFAR-data to some location in your computer. 
# Then, take this code and fix the path so that it finds the data from the right 
# location on your computer. Then the code goes through the data and it should
# randomly show some images from the data. Take a screenshot. 
# After that you can move into phases 2-4 of the assignment to write the 
# three functions. 

import pickle
import numpy as np
import matplotlib.pyplot as plt
from random import random

def unpickle(file):
    with open(file, 'rb') as f:
        dict = pickle.load(f, encoding="latin1")
    return dict

datadict = unpickle('/home/kamarain/Data/cifar-10-batches-py/data_batch_1')
#datadict = unpickle('/home/kamarain/Data/cifar-10-batches-py/test_batch')

X = datadict["data"]
Y = datadict["labels"]

print(X.shape)

labeldict = unpickle('/home/kamarain/Data/cifar-10-batches-py/batches.meta')
label_names = labeldict["label_names"]

X = X.reshape(10000, 3, 32, 32).transpose(0,2,3,1).astype("uint8")
Y = np.array(Y)

for i in range(X.shape[0]):
    # Show some images randomly
    if random() > 0.999:
        plt.figure(1);
        plt.clf()
        plt.imshow(X[i])
        plt.title(f"Image {i} label={label_names[Y[i]]} (num {Y[i]})")
        plt.pause(1)
