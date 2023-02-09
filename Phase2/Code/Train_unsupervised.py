import torch
from torch.utils.tensorboard import SummaryWriter
import torchvision.transforms as T
import torch.optim as optim
import matplotlib.pyplot as plt
import cv2
import sys
import os
import numpy as np
import argparse
from natsort import natsorted
import random
# import kornia
from tqdm.notebook import tqdm
#os.chdir("D:\Computer Vision\sparashar_p1\Phase2\Code")
from Model_unsupervised import HNet

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def getImageNames(path):
    
    image_names = []
    for file in os.listdir(path):
        image_names.append(os.path.splitext(file)[0])
    sorted_names = natsorted(image_names)
    
    return sorted_names

def generateBatch2(path_A, path_B, coordinates_path, path_cA, path_IA, batch_size=8):
    
    img_batch = []
    labels_batch = []
    c_labels_batch = []
    I_path_batch = []
    image_num = 0
    coordinates = np.load(coordinates_path)
    c_coordinates = np.load(path_cA)
    
    while image_num < batch_size:
        
        # Random Image Path
        image_names = getImageNames(path_A)             # Names are the same for both patch A and patch B
        I_names = getImageNames(path_IA)
        RandIdx = random.randint(0, len(image_names)-1)
        I_idx = RandIdx//3

        image_pathA = path_A + '/' + image_names[RandIdx] + '.jpg'
        image_pathB = path_B + '/' + image_names[RandIdx] + '.jpg'
        I_path_batch.append(path_IA + '/' + I_names[I_idx] + '.jpg')
        
        image_num += 1

        # Read Data

        imgA = cv2.imread(image_pathA, cv2.IMREAD_GRAYSCALE)
        imgB = cv2.imread(image_pathB, cv2.IMREAD_GRAYSCALE)
        
        label = coordinates[RandIdx]
        c_label = c_coordinates[RandIdx]
        
        # Normalize Data and convert to torch tensors

        imgA = torch.from_numpy((imgA.astype(float) - 127.5) / 127.5)
        imgB = torch.from_numpy((imgB.astype(float) - 127.5) / 127.5)
        imgA=imgA.to(torch.float)
        imgB=imgB.to(torch.float)
        label = torch.from_numpy(label.astype(float)/32.)
        c_label = torch.from_numpy(c_label.astype(float))
        
        # Stack grayscale images
        img = torch.stack((imgA, imgB), dim=0)

        img_batch.append(img.to(device))
        labels_batch.append(label.to(device))
        c_labels_batch.append(c_label.to(device))
           
    return torch.stack(img_batch), torch.stack(labels_batch), torch.stack(c_labels_batch), I_path_batch
        

def generateBatch(path_A, path_B, coordinates_path, batch_size=64):
    
    img_batch = []
    labels_batch = []
    image_num = 0
    coordinates = np.load(coordinates_path)
    # print(coordinates.shape)
    
    while image_num < batch_size:
        
        # Random Image Path
        image_names = getImageNames(path_A)               # Names are the same for both patch A and patch B
        RandIdx = random.randint(0, len(image_names)-1)
        image_pathA = path_A + '/' + image_names[RandIdx] + '.jpg'
        image_pathB = path_B + '/' + image_names[RandIdx] + '.jpg'
        # print(image_pathA, image_pathB)
        # print(RandIdx)
        
        image_num += 1

        # Read Data
        imgA = cv2.imread(image_pathA, cv2.IMREAD_GRAYSCALE)
        imgB = cv2.imread(image_pathB, cv2.IMREAD_GRAYSCALE)
        
        label = coordinates[RandIdx]
        # print(label.shape)
        
        # Normalize Data and convert to torch tensors
        imgA = torch.from_numpy((imgA.astype(float) - 127.5) / 127.5)
        imgB = torch.from_numpy((imgB.astype(float) - 127.5) / 127.5)
        
        label = torch.from_numpy(label.astype(float)/32.)
        
        # Stack grayscale images
        img = torch.stack((imgA, imgB), dim=0)
        
        # Add to batch
        img_batch.append(img.to(device))
        labels_batch.append(label.to(device))
           
    return torch.stack(img_batch), torch.stack(labels_batch)

def prettyPrint(NumEpochs, MiniBatchSize):
    print("Number of Epochs Training will run for " + str(NumEpochs))
    print("Mini Batch Size " + str(MiniBatchSize))

def train(path_ATrain, path_BTrain,
        path_AVal, path_BVal,
        path_cATrain, path_IATrain,
        path_cAVal, path_IAVal,
        coordinates_path,
        batch_size, 
        num_epochs, 
        CheckPointPath):
    
    torch.cuda.empty_cache()
    history = []

    #Model 
    model = HNet().to(device)
    model = model.float()
    
    #Optimizer
    optimizer = optim.Adam(model.parameters(), lr=0.005)

    num_samples_train = len(getImageNames(path_ATrain))
    num_samples_val = len(getImageNames(path_AVal))
    
    num_iter_per_epoch = num_samples_train//batch_size
    num_iter_per_epoch_val = num_samples_val//batch_size
    
    
    for epoch in tqdm(range(num_epochs)):

        train_losses = []
        val_losses = []
        
        for iter_counter in tqdm(range(num_iter_per_epoch)):
            
            train_batch = generateBatch2(path_ATrain, path_BTrain, coordinates_path, 
                                        path_cATrain, path_IATrain, batch_size)
            
            # Train
            model.train()
            
            batch_loss_train = model.training_step(train_batch)
            # print(batch_loss_train)
            train_losses.append(batch_loss_train)
            # batch_loss_train = torch.tensor(batch_loss_train)
            batch_loss_train.backward()
            optimizer.step()
            optimizer.zero_grad()   
        
        # Save model every epoch
        SaveName = CheckPointPath + str(epoch) + "_model.ckpt"
        torch.save(
            {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "loss": batch_loss_train,
            },
            SaveName,
        )
        print("\n" + SaveName + " Model Saved...")


        # Evaluate
        
        model.eval()
        with torch.no_grad():
            for iter_count_val in tqdm(range(num_iter_per_epoch_val)):
                val_batch = generateBatch2(path_AVal, path_BVal, coordinates_path, 
                                        path_cAVal, path_IAVal, batch_size)
                batch_loss_val = model.validation_step(val_batch)
                print(batch_loss_val)
                val_losses.append(batch_loss_val)
                
        result = model.validation_end(val_losses)
        result['train_loss'] = torch.stack(train_losses).mean().item()
        model.epoch_end(epoch, result)
        history.append(result)
        np.save('epoch_history.npy', np.array(history))
        plotLosses(history)
        
    return history
    
def plotLosses(history):
    train_losses = [x['train_loss'] for x in history]
    val_losses = [x['val_loss'] for x in history]
    plt.figure()
    plt.plot(train_losses, '-b')
    plt.plot(val_losses, '-r')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend(['Training', 'Validation'])
    plt.title('Loss vs. Epoch')
    plt.savefig('LossCurve.png')
    
    

def main():
    
    Parser = argparse.ArgumentParser()
    Parser.add_argument(
        "--BasePath",
        default="../Data",
        help="Base path of images, Default:../Data",
    )
    Parser.add_argument(
        "--CheckPointPath",
        default="../Checkpoints/",
        help="Path to save Checkpoints, Default: ../Checkpoints/",
    )
    Parser.add_argument(
        "--NumEpochs",
        type=int,
        default=50,
        help="Number of Epochs to Train for, Default:50",
    )
    Parser.add_argument(
        "--MiniBatchSize",
        type=int,
        default=16,
        help="Size of the MiniBatch to use, Default:2",
    )

    Args = Parser.parse_args()
    num_epochs = Args.NumEpochs
    BasePath = Args.BasePath
    batch_size = Args.MiniBatchSize
    CheckPointPath = Args.CheckPointPath

    path_ATrain = BasePath + "/modified_train/patchA"
    path_BTrain = BasePath + "/modified_train/patchB"
    path_AVal = BasePath + "/modified_val/patchA"
    path_BVal = BasePath + "/modified_val/patchB"
    coordinates_path = BasePath + '/modified_train_labels.npy'
    path_cATrain = '../Data/train_cornerpoints.npy'
    path_cAVal = '../Data/val_cornerpoints.npy'
    path_IATrain = '../Data/Train'
    path_IAVal = '../Data/Val' 

    # print(getImageNames(path_AVal))

    prettyPrint(num_epochs, batch_size)

    history = []

    history += train(path_ATrain, path_BTrain,
        path_AVal, path_BVal,
        path_cATrain, path_IATrain,
        path_cAVal, path_IAVal,
        coordinates_path,
        batch_size, 
        num_epochs, 
        CheckPointPath)

    np.save('history.npy', np.array(history))
    plotLosses(history)
    

    



if __name__ == "__main__":
    main()
