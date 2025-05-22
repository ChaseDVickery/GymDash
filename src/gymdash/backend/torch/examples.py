import os
import pathlib
from collections import OrderedDict
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader
    from torchvision import datasets
    from torchvision.transforms import ToTensor
    _has_torch = True
except ImportError:
    _has_torch = False

from gymdash.backend.torch.utils import get_available_accelerator

device = get_available_accelerator()

class ClassifierMNIST(nn.Module):
    def __init__(self) -> None:
        if not _has_torch:
            raise ImportError(f"Install pytorch to use example model {type(self)}.")
        super().__init__()
        # Input: Nx1x28x28
        self.layers = nn.Sequential(OrderedDict([
            # Nx1x28x28
            ("conv1", nn.Conv2d(1,16,7)),
            # Nx16x22x22
            ("relu1", nn.ReLU()),
            # Nx16x22x22
            ("conv2", nn.Conv2d(16,32,5)),
            # Nx32x18x18
            ("relu2", nn.ReLU()),
            # Nx32x18x18
            ("conv3", nn.Conv2d(32,64,3)),
            # Nx64x16x16
            ("relu3", nn.ReLU()),
            # Nx64x16x16
            ("flatten", nn.Flatten()),
            # Nx64x16x16
            ("linear1", nn.Linear(16384, 2048)),
            ("relu4", nn.ReLU()),
            # Nx2048
            ("linear2", nn.Linear(2048, 256)),
            ("relu5", nn.ReLU()),
            # Nx256
            ("output", nn.Linear(256, 10))
        ]))

    def forward(self, x):
        logits = self.layers(x)
        return logits
    

def train_mnist_classifier(model: nn.Module, data_folder: str, **kwargs):
    # Setup folders
    train_path = os.path.join(data_folder, "train")
    test_path = os.path.join(data_folder, "test")
    pathlib.Path(train_path).mkdir(parents=True, exist_ok=True)
    pathlib.Path(test_path).mkdir(parents=True, exist_ok=True)
    # Get the dataset
    train_data = datasets.MNIST(
        root=train_path,
        train=True,
        download=True,
        transform=ToTensor(),
    )
    # Train the model
    tb_logger = kwargs.get("tb_logger", None)
    log_step = kwargs.get("log_step", 100)
    batch_size = kwargs.get("batch_size", 64)
    shuffle = kwargs.get("shuffle", False)
    loss_fn = nn.CrossEntropyLoss()
    optimizer = torch.optim.SGD(model.parameters(), lr=1e-3)
    train_dataloader = DataLoader(train_data, batch_size, shuffle)
    size = len(train_dataloader.dataset)
    model.train()
    for batch, (x, y) in enumerate(train_dataloader):
        x, y = x.to(device), y.to(device)

        pred = model(x)
        loss = loss_fn(pred, y)

        loss.backward()
        optimizer.step()
        optimizer.zero_grad()

        if batch%log_step == 0:
            loss, current = loss.item(), (batch + 1) * len(x)
            print(f"loss: {loss:>7f}  [{current:>5d}/{size:>5d}]")
    
