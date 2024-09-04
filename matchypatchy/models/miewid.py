from PIL import Image
import torch
import torchvision.transforms as transforms
import numpy as np



from PIL import Image,  ImageFile
from numpy import max
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms.functional as F
from torchvision.transforms import (Compose, Resize, Normalize, ToTensor)



preprocess = Compose([Resize((440, 440)),
                      ToTensor(),
                      Normalize(mean=[0.485, 0.456, 0.406],
                                std=[0.229, 0.224, 0.225]),])


class ImageGenerator(Dataset):
    '''
    Data generator that crops images on the fly, requires relative bbox coordinates,
    ie from MegaDetector

    Options:
        - resize: dynamically resize images to target (square) [W,H]
    '''
    def __init__(self, x, resize_height=440, resize_width=440):
        self.x = x
        self.resize_height = int(resize_height)
        self.resize_width = int(resize_width)
        self.transform = transforms.Compose([Resize((self.resize_height, self.resize_width)),
                                             ToTensor(),
                                             Normalize(mean=[0.485, 0.456, 0.406],
                                                       std=[0.229, 0.224, 0.225]),])

    def __len__(self):
        return len(self.x)

    def __getitem__(self, idx):
        image_name = self.x.loc[idx, self.file_col]

        try:
            img = Image.open(image_name).convert('RGB')
        except OSError:
            print("File error", image_name)
            del self.x.iloc[idx]
            return self.__getitem__(idx)

        width, height = img.size

        if self.crop:
            bbox1 = self.x['bbox_x'].iloc[idx]
            bbox2 = self.x['bbox_y'].iloc[idx]
            bbox3 = self.x['bbox_w'].iloc[idx]
            bbox4 = self.x['bbox_h'].iloc[idx]

            left = width * bbox1
            top = height * bbox2
            right = width * (bbox1 + bbox3)
            bottom = height * (bbox2 + bbox4)

            img = img.crop((left, top, right, bottom))

        img_tensor = self.transform(img)
        img.close()

        return img_tensor
    
    


def dataloader(manifest, batch_size=1, workers=1, resize_height=440, resize_width=440):
    '''
        Loads a dataset and wraps it in a PyTorch DataLoader object.
        Always dynamically crops

        Args:
            - manifest (DataFrame): data to be fed into the model
            - batch_size (int): size of each batch
            - workers (int): number of processes to handle the data
            - file_col: column name containing full file paths
            - crop (bool): if true, dynamically crop images
            - normalize (bool): if true, normalize array to values [0,1]
            - resize_width (int): size in pixels for input width
            - resize_height (int): size in pixels for input height

        Returns:
            dataloader object
    '''
    dataset_instance = ImageGenerator(manifest, resize_height=440, resize_width=440)

    dataLoader = DataLoader(
            dataset=dataset_instance,
            batch_size=batch_size,
            shuffle=False,
            num_workers=workers
        )
    return dataLoader


def load_miew(file_path):
    model = torch.load(file_path)
    return model


def extract_roi_embedding(model, dataloader):
    with torch.no_grad():
        output = model(dataloader)

    print(output)
    print(output.shape)
    return output


model = load_miew('/home/kyra/matchypatchy/matchypatchy/models/miew_id/miew_id_all.bin')
extract_roi_embedding(model, dataloader)