import torch
from torch import nn
import torch.nn.functional as F
from torchvision import transforms
import time
import json
import mss
import numpy as np
from PIL import Image
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# get block's id
with open(os.path.join(BASE_DIR, "idx_to_blockid.json"), "r") as f:
    class_map = {int(k): int(v) for k, v in json.load(f).items()}

# get block's name
with open(os.path.join(BASE_DIR, "blockid_to_name.json"), "r") as f:
    block_id_to_name = {int(k): v for k, v in json.load(f).items()}

# CNN definition
class CNN(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 16, 3, padding=1)
        self.conv2 = nn.Conv2d(16, 32, 3, padding=1)
        self.pool = nn.MaxPool2d(2)
        self.fc1 = nn.Linear(32 * 16 * 16, 128)
        self.fc2 = nn.Linear(128, num_classes)

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = x.view(x.size(0), -1)
        x = F.relu(self.fc1(x))
        return self.fc2(x)

# models
num_classes = len(class_map)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = CNN(num_classes=num_classes)
model.load_state_dict(
    torch.load("CNN\minecraft_blocks_new_model_2.pth", map_location=device)
)
model.to(device)
model.eval()

# transform image
transform = transforms.Compose([
    transforms.Resize((64, 64)),
    transforms.ToTensor(),
    transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
])

# screenshot
def grab_center():
    with mss.mss() as sct:
        monitor = sct.monitors[1]  
        cx = monitor["width"] // 2
        cy = monitor["height"] // 2
        bbox = {
            "left": cx - 64,
            "top": cy - 64,
            "width": 128,
            "height": 128
        }
        img = np.array(sct.grab(bbox)) 
        # Windows: RGB  Ubuntu: BGR
        img = Image.fromarray(img[:, :, [2,1,0]]).convert("RGB")
        return img


def recognize_block():
    img = grab_center()
    img_tensor = transform(img).unsqueeze(0).to(device)

    with torch.no_grad():
        pred_idx = model(img_tensor).argmax(1).item()

    block_id = class_map[pred_idx]
    block_name = block_id_to_name.get(block_id, "UNKNOWN")

    return block_id, block_name

print("Vision System Running...")

while True:
    block_id, block_name = recognize_block()
    output = str(block_name) + " ID:" + str(block_id)
    sys.stdout.write("\r" + output + "                     ")
    sys.stdout.flush()
    time.sleep(0.5)
