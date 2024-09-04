from PIL import Image,  ImageFile
from numpy import max
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms.functional as F
from torchvision.transforms import (Compose, Resize, ToTensor)

ImageFile.LOAD_TRUNCATED_IMAGES = True


# MIEWID takes 480x480



class SquarePad:
    def __call__(self, image):
        size = image.size()
        max_wh = max(size)
        hp = int((max_wh - size[-1]) / 2)
        vp = int((max_wh - size[-2]) / 2)
        padding = (hp, vp, hp, vp)
        return F.pad(image, padding, 0, 'constant')


class ImageGenerator(Dataset):
    '''
    Data generator that crops images on the fly, requires relative bbox coordinates,
    ie from MegaDetector

    Options:
        - file_col: column name containing full file paths
        - resize: dynamically resize images to target (square) [W,H]
    '''
    def __init__(self, x, file_col='file', resize_height=480, resize_width=480):
        self.x = x
        self.file_col = file_col
        self.resize_height = int(resize_height)
        self.resize_width = int(resize_width)
        self.transform = Compose([
            SquarePad(),
            # torch.resize order is H,W
            Resize((self.resize_height, self.resize_width)),
            ToTensor(),
            ])

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
            bbox1 = self.x['bbox1'].iloc[idx]
            bbox2 = self.x['bbox2'].iloc[idx]
            bbox3 = self.x['bbox3'].iloc[idx]
            bbox4 = self.x['bbox4'].iloc[idx]

            left = width * bbox1
            top = height * bbox2
            right = width * (bbox1 + bbox3)
            bottom = height * (bbox2 + bbox4)

            left = max(0, int(left) - self.buffer)
            top = max(0, int(top) - self.buffer)
            right = min(width, int(right) + self.buffer)
            bottom = min(height, int(bottom) + self.buffer)
            img = img.crop((left, top, right, bottom))

        img_tensor = self.transform(img)
        img.close()

        if not self.normalize:  # un-normalize
            img_tensor = img_tensor * 255

        return img_tensor, image_name
    
    


def dataloader(manifest, batch_size=1, workers=1, file_col="file"):
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
    
    # default values file_col='file', resize=299
    dataset_instance = ImageGenerator(manifest)

    dataLoader = DataLoader(
            dataset=dataset_instance,
            batch_size=batch_size,
            shuffle=False,
            num_workers=workers
        )
    return dataLoader
