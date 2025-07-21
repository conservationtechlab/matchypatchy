import os
from PIL import Image, ImageOps
import math
import numpy as np
import pandas as pd
import torchvision.transforms as transforms

class XAIDataset:
    def __init__(self, df, img_size=(440,440), img_transform=None, img_path=""):
        assert isinstance(df, pd.DataFrame), "df must be a pandas DataFrame object"
        for col in {"annot", "image", "name"}:
            assert col in df.columns, f'df must contain column {col}'
        if "x" in df.columns:
            self.bbox = True
            for col in {"x", "y", "w", "h"}:
                assert col in df.columns, f'if using bounding boxes, df must contain column {col}'
        else:
            self.bbox = False

        self.theta = "theta" in df.columns

        self.df = df
        self.img_size = img_size
        self.img_transform = img_transform
        self.img_path = img_path
    
    def _load_image(self, row, transform=True):
        annot = row["annot"]
        img_path = os.path.join(self.img_path, row["image"])
        name = row["name"]   

        with open(img_path, "rb") as f:
            img = ImageOps.exif_transpose(Image.open(f))
            img.load()

        if self.bbox:
            x, y, w, h = row["x"], row["y"], row["w"], row["h"]
            if w <= 1:
                x = x * img.width
                y = y * img.height
                w = w * img.width
                h = h * img.height
                
            img = img.crop((x, y, min(x + w, img.width), min(y + h, img.height)))
        if self.theta:
            img = img.rotate(math.degrees(row["theta"]))
            
        img = transforms.Resize(self.img_size)(img)

        if transform and self.img_transform:
            return self.img_transform(img), name, annot

        return np.array(img), name, annot


    def __len__(self):
        return len(self.df)
        
    def __getitem__(self, idx):
        return self._load_image(self.df.iloc[idx])

    def get_image_pretransform(self, annot_id):
        selected_row = self.df[self.df["annot"] == annot_id]
        assert len(selected_row) == 1, f'{len(selected_row)} rows found in df with annot={annot_id}'
        return self._load_image(selected_row.iloc[0], transform=False)

    def get_image_transformed(self, annot_id):
        selected_row = self.df[self.df["annot"] == annot_id]
        assert len(selected_row) == 1, f'{len(selected_row)} rows found in df with annot={annot_id}'
        return self._load_image(selected_row.iloc[0])

    def save_df(self, output_dir):
        self.df.to_csv(os.path.join(output_dir, 'df.csv'), index=False)
    
    def get_img_pair(self, device, annot_0, annot_1):
        img_0, _, _ = self.get_image_transformed(annot_0)
        img_1, _, _ = self.get_image_transformed(annot_1)

        img_0 = img_0.unsqueeze(0).to(device)
        img_1 = img_1.unsqueeze(0).to(device)

        img_np_0, _, _ = self.get_image_pretransform(annot_0)
        img_np_1, _, _ = self.get_image_pretransform(annot_1)

        return img_0, img_1, img_np_0, img_np_1

def get_img_pair_from_paths(device, img0, img1, img_size, img_transform):

    def get_img_pair_from_path(roi, transform):
        with open(roi['filepath'], "rb") as f:
            image = ImageOps.exif_transpose(Image.open(f))
            image.load()
            image = crop(roi, image)

            image = transforms.Resize(img_size)(image)

            if transform:
                return img_transform(image).unsqueeze(0).to(device)

            return np.array(image)
        
    def crop(roi, img):
        x, y, w, h = roi["bbox_x"], roi["bbox_y"], roi["bbox_w"], roi["bbox_h"]
        if w <= 1:
            x = x * img.width
            y = y * img.height
            w = w * img.width
            h = h * img.height
                
            img = img.crop((x, y, min(x + w, img.width), min(y + h, img.height)))

        return img
    
    return (get_img_pair_from_path(img0, transform=True),
            get_img_pair_from_path(img1, transform=True),
            get_img_pair_from_path(img0, transform=False),
            get_img_pair_from_path(img1, transform=False),)