import os
import pathlib
import re
from abc import abstractmethod, ABC
from collections import OrderedDict
from typing import Any, Dict, Union, Callable, Literal
from pathlib import Path
from torch.nn.modules import Module

from gymdash.backend.torch.utils import get_available_accelerator
from gymdash.backend.core.simulation.callbacks import (BaseCustomCallback,
                                                       EmptyCallback)
from gymdash.backend.core.simulation.base import StopSimException
from gymdash.backend.core.utils.state import SimpleStateStack

try:
    import torch
    import torch.nn as nn
    from torch.nn.modules.loss import _Loss
    from torch.optim import Optimizer
    from torch.utils.data import DataLoader
    from torch.utils.tensorboard.writer import SummaryWriter
    from torchvision import datasets
    from torchvision.transforms import ToTensor
    _has_torch = True
except ImportError:
    _has_torch = False

if not _has_torch:
    raise ImportError("Install pytorch to use base gymdash-pytorch utilities.")

class InferenceModel(ABC):
    @abstractmethod
    def produce(self, inputs):
        pass

class SimulationMLModel():
    STATE_TRAIN = "<<train>>"
    STATE_VAL = "<<val>>"
    STATE_TEST = "<<test>>"

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

        self._phase_callbacks: dict[str, dict[str, list[Callable]]] = {
            "train":    {"start": [], "end": []},
            "val":      {"start": [], "end": []},
            "test":     {"start": [], "end": []},
        }
        self.sm: SimpleStateStack = SimpleStateStack()

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

    def add_callback(self, phase: Literal["train", "test", "val", "all"], timing: Literal["start", "end", "all"], callback: Callable):
        phases = []
        timings = []
        if phase == "all":
            phases.append("train")
            phases.append("val")
            phases.append("test")
        else:
            phases.append(phase)
        if timing == "all":
            timings.append("start")
            timings.append("end")
        else:
            timings.append(timing)
        for p in phases:
            for t in timings:
                self._phase_callbacks[p][t].append(callback)

    @abstractmethod
    def _train(self, **kwargs):
        pass
    @abstractmethod
    def _validate(self, **kwargs):
        pass
    @abstractmethod
    def _test(self, **kwargs):
        pass
    
    def _invoke_callbacks(self, callback_list):
        for callback in callback_list:
            callback()

    @abstractmethod
    def _on_train_start(self, *args, **kwargs):
        pass
    @abstractmethod
    def _on_train_end(self, *args, **kwargs):
        pass
    @abstractmethod
    def _on_val_start(self, *args, **kwargs):
        pass
    @abstractmethod
    def _on_val_end(self, *args, **kwargs):
        pass
    @abstractmethod
    def _on_test_start(self, *args, **kwargs):
        pass
    @abstractmethod
    def _on_test_end(self, *args, **kwargs):
        pass

    def on_train_start(self, *args, **kwargs):
        self._on_train_start(*args, **kwargs)
        self._invoke_callbacks(self._phase_callbacks["train"]["start"])
    def on_train_end(self, *args, **kwargs):
        self._on_train_end(*args, **kwargs)
        self._invoke_callbacks(self._phase_callbacks["train"]["end"])
    def on_val_start(self, *args, **kwargs):
        self._on_val_start(*args, **kwargs)
        self._invoke_callbacks(self._phase_callbacks["val"]["start"])
    def on_val_end(self, *args, **kwargs):
        self._on_val_end(*args, **kwargs)
        self._invoke_callbacks(self._phase_callbacks["val"]["end"])
    def on_test_start(self, *args, **kwargs):
        self._on_test_start(*args, **kwargs)
        self._invoke_callbacks(self._phase_callbacks["test"]["start"])
    def on_test_end(self, *args, **kwargs):
        self._on_test_end(*args, **kwargs)
        self._invoke_callbacks(self._phase_callbacks["test"]["end"])

    def train(self, *args, **kwargs):
        self._is_training = True
        try:
            self.on_train_start(*args, **kwargs)
            self.sm.push_state(SimulationMLModel.STATE_TRAIN)
            self._train(**kwargs)
        except Exception as e:
            self._is_training = False
            raise e
        finally:
            self.on_train_end(*args, **kwargs)
            self.sm.pop_state()
            self._is_training = False
    def test(self, *args, **kwargs):
        self._is_testing = True
        try:
            self.on_test_start(*args, **kwargs)
            self.sm.push_state(SimulationMLModel.STATE_TEST)
            test_results = self._test(**kwargs)
            self.sm.pop_state()
        except Exception as e:
            self._is_testing = False
            raise e
        finally:
            self.on_test_end(*args, **kwargs)
            self.sm.pop_state()
        self._is_testing = False
        return test_results
    def validate(self, *args, **kwargs):
        print(f"validate called: args=({args}), kwargs=({kwargs})")
        self._is_validating = True
        try:
            self.on_val_start(*args, **kwargs)
            self.sm.push_state(SimulationMLModel.STATE_VAL)
            val_results = self._validate(**kwargs)
            self.sm.pop_state()
        except Exception as e:
            self._is_validating = False
            raise e
        finally:
            self.on_val_end(*args, **kwargs)
            self.sm.pop_state()
        self._is_validating = False
        return val_results
    def inference(self, **kwargs):
        pass
    

class SimpleClassifierMLModel(SimulationMLModel, InferenceModel):

    TRAINING_CKPT_PATTERN: re.Pattern = re.compile("train_ckpt_[0-9]+\.pt")
    TRAINING_CKPT_FORMAT: str = "train_ckpt_{0}.pt"
    TRAINING_CKPT_EXTRACTOR = lambda n: int(n.split("_")[-1].split(".")[0])

    def __init__(self, model: Module) -> None:
        super().__init__(model)

    def produce(self, inputs: Union[torch.Tensor, torch.utils.data.Dataset]) -> tuple[torch.Tensor, torch.Tensor]:
        """Given an input dataset, returns a tuple containing the classifier
        predictions and the ground-truth values of each sample, if provided.
        If 'inputs' is a Dataset, then both predictions and ground truth values
        are returned. If 'inputs' is a Tensor, then it is treated as only inputs,
        returning a tuple where the ground truth element is None."""
        device = get_available_accelerator()
        # Setup
        model               = self.model
        # Train
        model.eval()
        model.to(device)
        if isinstance(inputs, torch.Tensor):
            with torch.no_grad():
                inputs = inputs.to(device)
                pred = model(inputs)
                predictions = pred.argmax(1)
                return (predictions, None)
        elif isinstance(inputs, torch.utils.data.Dataset):
            tensors = []
            gts = []
            dl = DataLoader(inputs, batch_size=1, shuffle=False)
            with torch.no_grad():
                for (x,y) in dl:
                    x = x.to(device)
                    pred = model(x)
                    predictions = pred.argmax(1)
                    tensors.append(predictions)
                    gts.append(y)
            return (torch.cat(tensors), torch.cat(gts))

    def _train(self,
        dataloader: DataLoader,
        epochs:     int                             = 1,
        tb_logger:  Union[SummaryWriter, str, None] = None,
        log_step:   int                             = -1,
        loss_fn:    _Loss                           = nn.CrossEntropyLoss(),
        optimizer:  Optimizer                       = None,
        do_val:     bool                            = False,
        val_per_steps:  int                         = -1,
        val_per_epochs:  int                         = -1,
        val_kwargs:     Dict[str, Any]              = {},
        step_callback: BaseCustomCallback           = EmptyCallback(),
        epoch_callback: BaseCustomCallback          = EmptyCallback(),
        val_step_callback: BaseCustomCallback       = EmptyCallback(),
        ckpt_per_epochs: int                        = -1,
        ckpt_folder: Union[None, str, Path]         = None,
        device                                      = None,
        **kwargs
    ):
        step_callback.on_process_start(locals(), globals())
        epoch_callback.on_process_start(locals(), globals())
        step_callback.push_state("train")
        epoch_callback.push_state("train")
        # Get device
        if device is None:
            device = get_available_accelerator()
        # Setup tensorboard logger
        if isinstance(tb_logger, str):
            tb_logger = SummaryWriter(tb_logger)
        # Setup
        do_save_ckpt        = (ckpt_per_epochs > 0) and (ckpt_folder is not None)
        ckpt                = 1
        model               = self.model
        train_dataloader    = dataloader
        size                = len(train_dataloader.dataset)
        total_steps         = epochs * len(train_dataloader)
        loss_fn             = loss_fn \
            if loss_fn is not None \
            else nn.CrossEntropyLoss()
        optimizer           = optimizer \
            if optimizer is not None \
            else torch.optim.SGD(model.parameters())
        if do_save_ckpt:
            ckpt_folder: Path = Path(ckpt_folder)
            ckpt_folder.mkdir(parents=True, exist_ok=True)
        # Train
        model.to(device)
        model.train()
        curr_steps = 0
        curr_samples = 0
        logged_correct = 0
        logged_samples = 0
        logged_batches = 0
        logged_loss = 0
        for epoch in range(1, epochs+1):
            for batch, (x, y) in enumerate(train_dataloader):
                x, y = x.to(device), y.to(device)

                pred = model(x)
                loss = loss_fn(pred, y)
                # Calculate summed logs
                logged_loss += loss.item()
                logged_correct += (pred.argmax(1) == y).type(torch.float).sum().item()

                loss.backward()
                optimizer.step()
                optimizer.zero_grad()

                curr_steps      += 1
                logged_batches  += 1
                curr_samples    += len(x)
                logged_samples  += len(x)
                
                # Log loss
                if log_step > 0 and batch%log_step == 0:
                    # train_loss = loss.item()
                    l_loss      = logged_loss / logged_batches
                    l_accuracy  = logged_correct / logged_samples
                    logged_loss     = 0
                    logged_correct  = 0
                    logged_samples  = 0
                    logged_batches  = 0
                    if tb_logger is not None:
                        tb_logger.add_scalar("loss/train/train", l_loss, curr_samples)
                        tb_logger.add_scalar("acc/train/train", l_accuracy, curr_samples)
                        
                # Validate every val_per_steps steps
                if do_val and val_per_steps > 0 and (curr_steps % val_per_steps  == 0):
                    model.eval()
                    val_results = self.validate(
                        device=device,
                        loss_fn=loss_fn,
                        **val_kwargs
                    )
                    model.train()
                    if tb_logger is not None and val_results is not None:
                        val_loss = val_results["loss"]
                        val_accuracy = val_results["accuracy"]
                        tb_logger.add_scalar("loss/train/val", val_loss, curr_samples)
                        tb_logger.add_scalar("acc/train/val", val_accuracy, curr_samples)
                # Perform callback
                step_callback.update_locals(locals())
                if not step_callback.on_invoke():
                    raise StopSimException(f"Invocation of training step_callback at state '{step_callback.state}' terminated training.")
            # Save checkpoint every ckpt_per_epochs epochs
            if do_save_ckpt and (epoch % ckpt_per_epochs == 0):
                torch.save(self.model.state_dict(), ckpt_folder.joinpath(f"train_ckpt_{ckpt}.pt"))
                ckpt += 1
            # Validate every val_per_epochs epochs
            if do_val and val_per_epochs > 0 and (epoch % val_per_epochs == 0):
                model.eval()
                val_results = self.validate(
                    device=device,
                    loss_fn=loss_fn,
                    step_callback=val_step_callback,
                    **val_kwargs
                )
                model.train()
                if tb_logger is not None and val_results is not None:
                    val_loss = val_results["loss"]
                    val_accuracy = val_results["accuracy"]
                    tb_logger.add_scalar("loss/train/val", val_loss, curr_samples)
                    tb_logger.add_scalar("acc/train/val", val_accuracy, curr_samples)
            # Perform callback
            epoch_callback.update_locals(locals())
            if not epoch_callback.on_invoke():
                raise StopSimException(f"Invocation of training epoch_callback at state '{epoch_callback.state}' terminated training.")
        # Pop callback states
        step_callback.pop_state()
        epoch_callback.pop_state()
        
    def _testing_loop(
        self,
        dataloader: DataLoader,
        loss_fn:    _Loss                           = None,
        step_callback: BaseCustomCallback           = EmptyCallback(),
        device                                      = None,
        **kwargs
    ):
        if dataloader is None:
            return None
        # Get device
        if device is None:
            device = get_available_accelerator()
        # Setup
        model               = self.model
        val_dataloader      = dataloader
        num_batches         = len(val_dataloader)
        num_samples         = len(val_dataloader.dataset)
        loss_fn             = loss_fn \
            if loss_fn is not None \
            else nn.CrossEntropyLoss()

        # Test batches
        model.to(device)
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
                # Custom validation/test callback
                step_callback.update_locals(locals())
                if not step_callback.on_invoke():
                    raise StopSimException(f"Invocation of validation step_callback terminated training.")

        test_loss /= num_batches
        accuracy = correct / num_samples
        return {
            "loss": test_loss,
            "correct_samples": correct,
            "total_samples": num_samples,
            "accuracy": accuracy
        }

    def _validate(
        self,
        dataloader: DataLoader,
        loss_fn:    _Loss                           = None,
        step_callback: BaseCustomCallback           = EmptyCallback(),
        tb_logger:  Union[SummaryWriter, str, None] = None,
        device                                      = None,
        **kwargs
    ):
        # Setup tensorboard logger
        if isinstance(tb_logger, str):
            tb_logger = SummaryWriter(tb_logger)
        # Run tests
        test_results = self._testing_loop(
            dataloader,
            loss_fn,
            step_callback,
            device,
            **kwargs
        )
        has_logger = tb_logger is not None
        if has_logger:
            tb_logger.add_scalar("loss/val/val", test_results["loss"], 0)
            tb_logger.add_scalar("acc/val/val", test_results["accuracy"], 0)
        return test_results
    
    def _test(
        self,
        dataloader: DataLoader,
        loss_fn:    _Loss                           = None,
        step_callback: BaseCustomCallback           = EmptyCallback(),
        tb_logger:  Union[SummaryWriter, str, None] = None,
        device                                      = None,
        **kwargs
    ):
        # Setup tensorboard logger
        if isinstance(tb_logger, str):
            tb_logger = SummaryWriter(tb_logger)
        # Run tests
        test_results = self._testing_loop(
            dataloader,
            loss_fn,
            step_callback,
            device,
            **kwargs
        )
        has_logger = tb_logger is not None
        if has_logger:
            tb_logger.add_scalar("loss/test/test", test_results["loss"], 0)
            tb_logger.add_scalar("acc/test/test", test_results["accuracy"], 0)
        return test_results