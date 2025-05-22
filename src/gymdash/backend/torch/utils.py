import pkg_resources
import torch

def get_available_accelerator():
    torch_version = pkg_resources.get_distribution("torch").version
    if (torch_version >= '2.6.0'):
        # Does not work with old versions of PyTorch
        return torch.accelerator.current_accelerator().type if \
                    torch.accelerator.is_available() else \
                    "cpu"
    else:
        if torch.cuda.is_available():
            return torch.device("cuda")
        else:
            return torch.device("cpu")