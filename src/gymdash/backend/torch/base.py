import os
import pathlib
from abc import abstractmethod
from typing import Union, Dict, Any
from collections import OrderedDict

from torch.nn.modules import Module
try:
    from torch.utils.tensorboard.writer import SummaryWriter
    import torch
    import torch.nn as nn
    from torch.nn.modules.loss import _Loss
    from torch.optim import Optimizer
    from torch.utils.data import DataLoader
    from torchvision import datasets
    from torchvision.transforms import ToTensor
    _has_torch = True
except ImportError:
    _has_torch = False

if not _has_torch:
    raise ImportError("Install pytorch to use base gymdash-pytorch utilities.")

class SimulationMLModel():
    def __init__(self, model: nn.Module) -> None:
        self.model = model
        self.train_kwargs = {}
        self.val_kwargs = {}
        self.test_kwargs = {}
        self.inference_kwargs = {}

        self._is_training = False
        self._is_validating = False
        self._is_testing = False
        self._is_inferring = False

    @property
    def is_busy(self):
        return \
            self._is_training   or \
            self._is_validating or \
            self._is_testing    or \
            self._is_inferring

    def forward(self, x):
        return self.model.forward(x)
    
    def set_model(self, new_model: nn.Module):
        self.model = new_model

    @abstractmethod
    def _train(self, **kwargs):
        pass
    @abstractmethod
    def _validate(self, **kwargs):
        pass
    @abstractmethod
    def _test(self, **kwargs):
        pass
    
    def train(self, **kwargs):
        self._is_training = True
        self._train(**kwargs)
        self._is_training = False
    def test(self, **kwargs):
        self._is_testing = True
        self._test(**kwargs)
        self._is_testing = False
    def validate(self, **kwargs):
        self._is_validating = True
        val_results = self._validate(**kwargs)
        self._is_validating = False
        return val_results
    def inference(self, **kwargs):
        pass
    

class SimpleMLModel(SimulationMLModel):
    def __init__(self, model: Module) -> None:
        super().__init__(model)

    def _train(self,
        dataloader: DataLoader,
        epochs:     int                             = 1,
        tb_logger:  Union[SummaryWriter, str, None] = None,
        log_step:   int                             = -1,
        loss_fn:    _Loss                           = None,
        optimizer:  Optimizer                       = None,
        do_val:     bool                            = False,
        val_per_steps:  int                         = -1,
        val_per_epoch:  int                         = -1,
        val_kwargs:     Dict[str, Any]              = {},
        device                                      = None,
        **kwargs
    ):
        # Get device
        if device is None:
            device = torch.accelerator.current_accelerator().type if \
                torch.accelerator.is_available() else \
                "cpu"
        # Setup tensorboard logger
        if isinstance(tb_logger, str):
            tb_logger = SummaryWriter(tb_logger)
        # Setup
        model               = self.model
        train_dataloader    = dataloader
        size                = len(train_dataloader.dataset)
        loss_fn             = loss_fn \
            if loss_fn is not None \
            else nn.CrossEntropyLoss()
        optimizer           = optimizer \
            if optimizer is not None \
            else torch.optim.SGD(model.parameters(), lr=1e-3)

        # Train
        model.train()
        curr_steps = 0
        curr_samples = 0
        for epoch in range(1, epochs+1):
            print(f"BEGIN EPOCH: {epoch}")
            for batch, (x, y) in enumerate(train_dataloader):
                x, y = x.to(device), y.to(device)

                pred = model(x)
                loss = loss_fn(pred, y)

                loss.backward()
                optimizer.step()
                optimizer.zero_grad()

                curr_steps += 1
                curr_samples += len(x)
                
                # Log loss
                if log_step > 0 and batch%log_step == 0:
                    train_loss = loss.item()
                    if tb_logger is not None:
                        tb_logger.add_scalar("loss/train", train_loss, curr_samples)
                # Validate every val_per_steps steps
                if do_val and val_per_steps > 0 and (curr_steps % val_per_steps  == 0):
                    val_results = self.validate(
                        device=device,
                        loss_fn=loss_fn,
                        **val_kwargs
                    )
                    model.train()
                    if tb_logger is not None and val_results is not None:
                        val_loss = val_results["loss"]
                        accuracy = val_results["correct_samples"] \
                            / val_results["total_samples"]
                        tb_logger.add_scalar("loss/val", val_loss, curr_samples)
                        tb_logger.add_scalar("acc/val", accuracy, curr_samples)
            # Validate every val_per_epoch epochs
            if do_val and val_per_epoch > 0 and (epoch % val_per_epoch == 0):
                val_results = self.validate(
                    device=device,
                    loss_fn=loss_fn,
                    **val_kwargs
                )
                model.train()
                if tb_logger is not None and val_results is not None:
                    val_loss = val_results["loss"]
                    accuracy = val_results["correct_samples"] \
                        / val_results["total_samples"]
                    print(f"LOGGING loss/val: {val_loss}")
                    print(f"LOGGING acc/val: {accuracy}")
                    tb_logger.add_scalar("loss/val", val_loss, curr_samples)
                    tb_logger.add_scalar("acc/val", accuracy, curr_samples)

    def _validate(
        self,
        dataloader: DataLoader,
        loss_fn:    _Loss                           = None,
        device                                      = None,
        **kwargs
    ):
        print(f"THIS IS VAL DATALOADER: {dataloader}")
        print(f"THIS IS VAL KWARGS: {kwargs}")
        if dataloader is None:
            return None
        print(f"VAL HERE")
        # Get device
        if device is None:
            device = torch.accelerator.current_accelerator().type if \
                torch.accelerator.is_available() else \
                "cpu"
        # Setup
        model               = self.model
        val_dataloader      = dataloader
        num_batches         = len(val_dataloader)
        num_samples         = len(val_dataloader.dataset)
        loss_fn             = loss_fn \
            if loss_fn is not None \
            else nn.CrossEntropyLoss()

        # Train
        model.eval()
        correct = 0
        test_loss = 0
        with torch.no_grad():
            for batch, (x, y) in enumerate(val_dataloader):
                x, y = x.to(device), y.to(device)

                pred = model(x)
                loss = loss_fn(pred, y)
                # Sum up total loss over validation
                test_loss += loss.item()
                # Sum up total correct samples. We divide by total samples later
                correct += (pred.argmax(1) == y).type(torch.float).sum().item()
        test_loss /= num_batches
        print(f"VAL DONE: {correct}")
        return {
            "loss": test_loss,
            "correct_samples": correct,
            "total_samples": num_samples
        }
