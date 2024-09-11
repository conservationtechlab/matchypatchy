from PIL import Image
import torch
import torchvision.transforms as transforms
from transformers import AutoModel
import numpy as np


#model = AutoModel.from_pretrained("C:/Users/Kyra/matchypatchy/matchypatchy/models/miew_id/",trust_remote_code=True)

model = AutoModel.from_pretrained('C:/Users/tswanson/matchypatchy/matchypatchy/models/miew_id',trust_remote_code=True)
#print(model)pi
#torch.save(model.state_dict(), 'C:/Users/tswanson/matchypatchy/matchypatchy/models/miewid_v2.bin')
#load torch bin
#model = torch.load('C:/Users/tswanson/matchypatchy/matchypatchy/models/miewid_v2.bin')


def generate_random_image(height=440, width=440, channels=3):
    random_image = np.random.randint(0, 256, (height, width, channels), dtype=np.uint8)
    return Image.fromarray(random_image)

random_image = generate_random_image()

preprocess = transforms.Compose([
    transforms.Resize((440, 440)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

input_tensor = preprocess(random_image)
input_batch = input_tensor.unsqueeze(0) 

with torch.no_grad():
    output = model(input_batch)

print(output)
print(output.shape)
