import torch
import torch.nn.functional as F
import torch.optim as optim
from torch import nn
from torch.utils.data import DataLoader
from torchvision import transforms, datasets
import json

# 图像预处理
transform = transforms.Compose([
    transforms.Resize((64, 64)),      # 放大图片
    transforms.ToTensor(),             # 转化为张量
    transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
])

# 加载数据
data_path = r'E:\Git\mc_java\PyCraft_Python\CNN\minecraft_blocks_new_data'
ds = datasets.ImageFolder(data_path, transform = transform)

# 获取文件夹名到索引的映射
idx_to_class = {v: int(k) for k, v in ds.class_to_idx.items()}
with open("idx_to_blockid.json", "w") as f:
    json.dump(idx_to_class, f)


# 获取类别数量
num_classes = len(ds.classes)
# 定义DataLoader
train_loader = DataLoader(ds, batch_size=32, shuffle=True)

# CNN卷积神经网络模型
class CNN(nn.Module):
    def __init__(self, num_classes):
        super(CNN, self).__init__() # 继承
        # 第一层卷积层，输入通道为3，输出通道为16，卷积核大小为3*3，填充为1
        self.conv1 = nn.Conv2d(3, 16, kernel_size=3, padding=1)
        # 第二层卷积层，输入通道为16，输出通道为32，卷积核大小为3*3，填充为1
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, padding=1)
        # 最大池化层，池化核大小为2*2
        self.maxpool = nn.MaxPool2d(kernel_size=2)
        # 将特征展平为一维向量
        self.flatten = nn.Flatten()
        # 全连接层，输入特征维度为245，输出维度为10
        self.fc1 = nn.Linear(32*16*16, 128)
        self.fc2 = nn.Linear(128, num_classes)

    def forward(self, x):
        # 第一层卷积，使用ReLU激活函数
        x = F.relu(self.conv1(x)) # 64*64
        # 最大池化
        x = self.maxpool(x) # 卷积核大小减半32*32（通道数不变）
        # 第二层卷积，使用ReLU激活函数
        x = F.relu(self.conv2(x)) # 32*32
        # 再次最大池化
        x = self.maxpool(x) # 16*16
        # 将特征展平
        x = self.flatten(x) # 16*16*32
        # 全连接层
        x = self.fc1(x)
        # 使用ReLU激活函数
        x = F.relu(x)
        # 在使用一次全连接层
        x = self.fc2(x)
        # 使用对数softmax作为输出激活函数
        x = F.log_softmax(x, dim=1) # 将原始得的网络输出转换成概率分布，使得每个类别的输出值都在-无穷到1之间，并且所有类别的输出值之和为1
        return x
    
model = CNN(num_classes=num_classes)

# 定义损失函数和优化器
criterion = nn.NLLLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# 检查硬件
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
print(f"We are now using {device} for training.")

# 训练20个轮次
for epoch in range(20):
    running_loss = 0.0
    for i, (inputs, labels) in enumerate(train_loader):
        inputs = inputs.to(device)
        labels = labels.to(device)

        optimizer.zero_grad() # 梯度清零

        # 前向传播、反向传播、优化
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        if i % 5 == 4:
            print(f'[Epoch {epoch + 1}, Batch {i + 1}] Loss:{running_loss / 5:.3f}')
            running_loss = 0.0

print("The train was completed!")
# 保存模型
torch.save(model.state_dict(), "minecraft_blocks_new_model_2.pth")