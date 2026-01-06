import functools
import logging
import os
import pathlib
import time
import math
from typing import Union
from abc import abstractmethod
from gymdash.backend.core.utils.thread_utils import run_on_main_thread

import matplotlib.pyplot as plt
from torch import Tensor

import gymdash.backend.constants as constants
from gymdash.backend.core.simulation.callbacks import BaseCustomCallback, CallbackCustomList
from gymdash.backend.core.simulation.base import StopSimException
from gymdash.backend.torch.base import (InferenceModel,
                                        SimpleClassifierMLModel)
from gymdash.backend.enums import SimStatusCode, SimStatusSubcode
from gymdash.backend.core.api.models import SimStatus

try:
    from torch.utils.tensorboard import SummaryWriter
    _has_tb = True
except ImportError:
    _has_tb = False
try:
    import gymnasium as gym
    from gymnasium.wrappers import RecordVideo
    _has_gym = True
except ImportError:
    _has_gym = False
try:
    from stable_baselines3.a2c import A2C
    from stable_baselines3.common.logger import (TensorBoardOutputFormat,
                                                 configure)
    from stable_baselines3.ddpg import DDPG
    from stable_baselines3.dqn import DQN
    from stable_baselines3.ppo import PPO
    from stable_baselines3.sac import SAC
    from stable_baselines3.td3 import TD3
    _has_sb = True
except ImportError:
    _has_sb = False
try:
    import numpy as np
    _has_np = True
except ImportError:
    _has_np = False
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader
    from torchvision import datasets
    from torchvision.transforms import ToTensor
    _has_torch = True
except ImportError:
    _has_torch = False
from typing import Any, Dict

import gymdash.backend.core.api.config.stat_tags as stat_tags
from gymdash.backend.core.api.models import SimulationStartConfig
from gymdash.backend.core.simulation.base import Simulation
from gymdash.backend.core.simulation.manage import SimulationRegistry
from gymdash.backend.gymnasium.wrappers.MediaFileStatLinker import \
    MediaFileStatLinker
from gymdash.backend.gymnasium.wrappers.RecordVideoCustom import \
    RecordVideoCustom
from gymdash.backend.gymnasium.wrappers.RecordVideoToTensorboard import \
    RecordVideoToTensorboard
from gymdash.backend.gymnasium.wrappers.TensorboardStreamWrapper import (
    TensorboardStreamer, TensorboardStreamWrapper)
from gymdash.backend.stable_baselines.callbacks import \
    SimulationInteractionCallback
from gymdash.backend.tensorboard.MediaLinkStreamableStat import \
    MediaLinkStreamableStat
from gymdash.backend.torch.examples import (ClassifierMNIST,
                                            train_mnist_classifier)

logger = logging.getLogger(__name__)

class StableBaselinesSimulation(Simulation):
    def __init__(self, config: SimulationStartConfig) -> None:
        if not _has_gym:
            raise ImportError(f"Install gymnasium to use example simulation {type(self)}.")
        if not _has_sb:
            raise ImportError(f"Install stable_baselines3 to use example simulation {type(self)}.")

        super().__init__(config)
        self.algs = {
            "ppo":  PPO,
            "a2c":  A2C,
            "dqn":  DQN,
            "ddpg": DDPG,
            "td3":  TD3,
            "sac":  SAC,
        }

        self.tb_tag_key_map = {
            stat_tags.TB_SCALARS: ["rollout/ep_rew_mean", "train/learning_rate"],
            # stat_tags.TB_IMAGES: ["episode_video"]
        }

    def _get_help_text(self):
        help_text = f"""
{type(self)}:

Description: Run a limited number of StableBaselines simulations.

Supported Start Kwargs:
    num_steps: (int) Minimum number of steps to run simulation. Default 5000
    episode_trigger: (int) Input a value to record a video every x episodes. Input x<=0 for no recording. Default= 0.
    step_trigger: (int) Input a value to record a video every x steps. Input x<=0 for no recording. Default= 0.
    video_length: (int) Length of recorded episodes. Input x==0 for full episode. Default= 0.
    fps: (int) Frames-per-second of recorded video. Default= 30.
    env: (str) Name of Gymnasium environment to simulate. Default= CartPole-v1
    policy: (str) Name of stable baselines policy network to use. Default= MlpPolicy
    algorithm: (str) Name of RL algorithm to use. Options are ppo, a2c, dqn, ddpg, td3, sac. Default= ppo
    algorithm_kwargs: (dict) Dictionary of kwargs to pass to the algorithm. Default= {{}}
"""
        return help_text

    def _to_alg_initializer(self, alg_key: str):
        return self.algs.get(alg_key, self.algs["ppo"])

    def _create_streamers(self, kwargs: Dict[str, Any]):
        experiment_name = f"{kwargs['env']}_{kwargs['algorithm']}"
        tb_path = os.path.join("tb", experiment_name, "train")
        video_path = os.path.join(self.sim_path, "media", "episode_video")
        if self._project_info_set:
            tb_path = os.path.join(self.sim_path, tb_path)
        self.streamer.get_or_register(TensorboardStreamer(
            tb_path,
            self.tb_tag_key_map
        ))
        self.streamer.get_or_register(MediaFileStatLinker(
            "media_" + tb_path,
            [
                MediaLinkStreamableStat(
                    "episode_video",
                    stat_tags.VIDEOS,
                    video_path,
                    r"rl-video-(episode|step)-[0-9]+_[0-9]+\.mp4",
                    lambda fname: int(fname.split("_")[-1][:-4])
                )
            ]
        ))

    def create_kwarg_defaults(self):
        return {
            "num_steps":        5000,
            "episode_trigger":  lambda x: False,
            "step_trigger":     lambda x: False,
            "video_length":     0,
            "fps":              30,
            "env":              "CartPole-v1",
            "policy":           "MlpPolicy",
            "algorithm":        "ppo",
            "algorithm_kwargs": {}
        }
    # Policy use custom policy dict or existing policy network:
    # https://stable-baselines3.readthedocs.io/en/sde/guide/custom_policy.html

    def _setup(self, **kwargs):
        kwargs = self._overwrite_new_kwargs(self.kwarg_defaults, self.config.kwargs, kwargs)

    def _run(self, **kwargs):
        kwargs = self._overwrite_new_kwargs(self.kwarg_defaults, self.config.kwargs, kwargs)
        config = self.config

        # Check required kwargs
        num_steps           = kwargs["num_steps"]
        episode_trigger     = self._to_every_x_trigger(kwargs["episode_trigger"])
        step_trigger        = self._to_every_x_trigger(kwargs["step_trigger"])
        video_length        = kwargs["video_length"]
        fps                 = kwargs["fps"]
        policy              = kwargs["policy"]
        env_name            = kwargs["env"]
        algorithm           = self._to_alg_initializer(kwargs["algorithm"])
        alg_kwargs          = kwargs["algorithm_kwargs"]

        experiment_name = f"{env_name}_{kwargs['algorithm']}"
        tb_path = os.path.join("tb", experiment_name, "train")
        if self._project_info_set:
            tb_path = os.path.join(self.sim_path, tb_path)
        video_path = os.path.join(self.sim_path, "media", "episode_video")
        ckpt_path = os.path.join(self.sim_path, "checkpoints")

        try:
            env = gym.make(env_name, render_mode="rgb_array")
        except ValueError:
            env = gym.make(env_name)
        # Wrappers
        # Use StreamerRegistry to see if there is an existing Streamer with
        # the same streamer_name. In this case, the streamer_name checked is
        # just the tensorboard path (tb_path). This helps keep only one streamer
        # in charge of one tb folder.
        env = self.streamer.get_or_register(TensorboardStreamWrapper(
                env,
                tb_path,
                self.tb_tag_key_map
            ))
        self.streamer.get_or_register(MediaFileStatLinker(
            "media_" + tb_path,
            [
                MediaLinkStreamableStat(
                    "episode_video",
                    stat_tags.VIDEOS,
                    video_path,
                    r"rl-video-(episode|step)-[0-9]+_[0-9]+\.mp4",
                    lambda fname: int(fname.split("_")[-1][:-4])
                )
            ]
        ))
        # Record every X episodes to video.
        env = RecordVideoCustom(
            env,
            video_path,
            episode_trigger,
            step_trigger,
            video_length=video_length,
            fps=fps,
        )
        # Also Store the video record in the tb file.
        # r_env = RecordVideoToTensorboard(
        #     env,
        #     tb_path,
        #     episode_trigger,
        #     step_trigger,
        #     video_length=video_length, 
        #     fps=fps
        # )
        # env = r_env
        # Callbacks
        # Hook into the running simulation.
        # This callback provides communication channels between the
        # simulation and the user as the simulation runs.
        sim_interact_callback = SimulationInteractionCallback(self)
        # Logger
        backend_logger = configure(tb_path, ["tensorboard"])

        # Setup Model
        self.model = algorithm(
            policy,
            env,
            verbose=0,
            tensorboard_log=tb_path,
            **alg_kwargs
        )
        self.model.set_logger(backend_logger)
        tb_loggers = [t for t in self.model.logger.output_formats if isinstance(t, TensorBoardOutputFormat)]

        # Change the video recorder wrapper to point to the same SummaryWriter
        # as used by the model for recording stats.
        # r_env.configure_recorder("episode_video", tb_loggers[0].writer)

        # Train
        try:
            self.model.learn(total_timesteps=num_steps, progress_bar=False, callback=sim_interact_callback)
            # self.model.learn(total_timesteps=num_steps, progress_bar=True, callback=sim_interact_callback)
            self.model.save("ppo_aapl")
            was_cancelled = self.was_cancelled()
            if was_cancelled:
                self.add_status(SimStatus(
                    code=SimStatusCode.FAIL,
                    subcode=SimStatusSubcode.STOPPED,
                    details="Simulation stopped."
                ))
            else:
                self.add_status(SimStatus(
                    code=SimStatusCode.SUCCESS,
                    details="Simulation successfully run."
                ))
        except StopSimException as se:
            self._meta_failed = True
            self.add_status(SimStatus(
                code=SimStatusCode.FAIL,
                subcode=SimStatusSubcode.STOPPED,
                details="Simulation stopped."
            ))
        except Exception as e:
            self._meta_failed = True
            self.add_error_details(str(e))
            
        env.close()


class CustomControlSimulation(Simulation):
    def __init__(self, config: SimulationStartConfig) -> None:
        if not _has_np:
            raise ImportError(f"Install numpy to use example simulation {type(self)}.")
        if not _has_tb:
            raise ImportError(f"Install tensorboard to use example simulation {type(self)}.")
        super().__init__(config)

    def _get_help_text(self):
        help_text = f"""
{type(self)}:

Description: Run a custom simulation demonstrating interactive control requests. Every period, the simulation alters a scalar value (my_number). This occurs for some runtime, pausing a points specified by the user to wait for input before continuing.

Supported Start Kwargs:
    interactive: (bool) Boolean describing whether to use the interactive setup. Default= False.
    poll_period: (float) Time between each step. Default= 0.5.
    total_runtime: (float) Minimum runtime of the simulation. Default= 30.
    pause_points: (list[float]) List of values where the simulation pauses and asks for user input. Default= []
    other_kwargs: (None) N/A. Default= {{}}.
"""
        return help_text
        
    def _create_streamers(self, kwargs: Dict[str, Any]):
        experiment_name = f"custom"
        tb_path = os.path.join("tb", experiment_name)
        if self._project_info_set:
            tb_path = os.path.join(self.sim_path, tb_path)
        self.streamer.get_or_register(TensorboardStreamer(
            tb_path,
            {
                stat_tags.TB_SCALARS: ["my_number"],
            }
        ))

    def create_kwarg_defaults(self):
        return {
            "interactive":      False,
            "poll_period":      0.5,
            "total_runtime":    30,
            "pause_points":     [],
            "other_kwargs":     {}
        }

    def _setup(self, **kwargs):
        kwargs = self._overwrite_new_kwargs(self.kwarg_defaults, self.config.kwargs, kwargs)

    def _run(self, **kwargs):
        kwargs = self._overwrite_new_kwargs(self.kwarg_defaults, self.config.kwargs, kwargs)
        config = self.config

        # Check required kwargs
        interactive         = kwargs["interactive"]
        poll_period         = kwargs["poll_period"]
        total_runtime       = kwargs["total_runtime"]
        pause_points        = sorted(kwargs["pause_points"])
        other_kwargs        = kwargs["other_kwargs"]

        experiment_name = f"custom"
        tb_path = os.path.join("tb", experiment_name)
        if self._project_info_set:
            tb_path = os.path.join(self.sim_path, tb_path)

        # Wrappers
        # Use StreamerRegistry to see if there is an existing Streamer with
        # the same streamer_name. In this case, the streamer_name checked is
        # just the tensorboard path (tb_path). This helps keep only one streamer
        # in charge of one tb folder.
        tb_streamer = self.streamer.get_or_register(TensorboardStreamer(
                tb_path,
                {
                    stat_tags.TB_SCALARS: ["my_number"]
                }
            ))
        
        writer = SummaryWriter(tb_path)

        interactive_text = (
            "Interactive mode. Please send custom queries with any, all, or none "
            "of the folling keys. When done, send a custom query with the 'continue' key:\n"
            "\tpoll_period: float for the time between each stat logging.\n"
            "\ttotal_runtime: float representing the minimum total runtime of the simulation.\n"
            "\tpause_points: list of floats (e.g. [1, 3, etc...]) representing the times at which "
            "the simulation asks for input from the user before continuing.\n"
            "\tother_kwargs: Dictionary (subkwargs) for various other keyword arguments."
        )
        if interactive:
            self.interactor.add_control_request("custom_query", interactive_text)
            while True:
                # HANDLE INCOMING INFORMATION
                self.base_step()
                if self.interactor.set_out_if_in("stop_simulation", True):
                    self.set_cancelled()
                    writer.close()
                    return
                triggered, custom = self.interactor.get_in("custom_query")
                if triggered:
                    if "poll_period" in custom:
                        poll_period = custom["poll_period"]
                    if "total_runtime" in custom:
                        total_runtime = custom["total_runtime"]
                    if "pause_points" in custom:
                        pause_points = custom["pause_points"]
                    if "other_kwargs" in custom:
                        other_kwargs = custom["other_kwargs"]
                    self.interactor.set_out("custom_query", custom)
                    if "continue" in custom:
                        break
                    else:
                        time.sleep(0.1)

        st = time.time()
        try:
            step = 0
            timer = 0
            curr_pause_point = 0
            while (timer < total_runtime):
                self.base_step()
                # Manage pause points
                # Pause if we are at the next pause point time
                if curr_pause_point < len(pause_points) and timer >= pause_points[curr_pause_point]:
                    self.interactor.add_control_request("custom_query", "Please send custom_query with 'continue' key to continue.")
                    # Once we get a custom query with a "continue" key, then
                    # we can increment the pause point index and move on
                    while True:
                        # Handle normal
                        self.base_step()
                        self.interactor.set_out_if_in("progress", (timer, total_runtime))
                        # Handle custom
                        triggered, custom = self.interactor.get_in("custom_query")
                        if triggered and "continue" in custom:
                            self.interactor.set_out("custom_query", custom)
                            break
                        else:
                            time.sleep(0.1)
                        # HANDLE INCOMING INFORMATION
                        if self.interactor.set_out_if_in("stop_simulation", True):
                            self.set_cancelled()
                            writer.close()
                            return
                    curr_pause_point += 1
                start_time = time.time()
                # Perform functions
                writer.add_scalar("my_number", step + 4*np.random.random(), step)
                step += 1
                # Handle interactions
                self.interactor.set_out_if_in("progress", (timer, total_runtime))
                # HANDLE INCOMING INFORMATION
                if self.interactor.set_out_if_in("stop_simulation", True):
                    self.set_cancelled()
                    writer.close()
                    return
                # Sleep until the poll period is done
                end_time = time.time()
                time_taken = end_time - start_time
                sleep_time = max(poll_period - time_taken, 0)
                time.sleep(sleep_time)
                timer += max(time_taken, poll_period)
            
            self.add_status(SimStatus(
                code=SimStatusCode.SUCCESS,
                details="Simulation successfully run."
            ))
        except StopSimException as se:
            self._meta_failed = True
            self.add_status(SimStatus(
                code=SimStatusCode.FAIL,
                subcode=SimStatusSubcode.STOPPED,
                details="Simulation stopped"
            ))
        except Exception as e:
            self._meta_failed = True
            self.add_error_details(str(e))
            
        et = time.time()
        logger.debug(f"total time taken: {et-st}")
        writer.close()

class MLSimulationCallback(BaseCustomCallback):
    def __init__(self, simulation: Simulation):
        self.simulation = simulation
        super().__init__()
    @property
    def interactor(self):
        return self.simulation.interactor

class MLSimulationUpdateCallback(MLSimulationCallback):
    def __init__(self, simulation: Simulation):
        super().__init__(simulation)
    def _on_invoke(self):
        self.simulation.base_step()
        should_continue = True
        if self.simulation.sm.state == "<<train>>":
            curr_steps = self.locals.get("curr_steps", 0)
            total_steps = self.locals.get("total_steps", 1)
            # HANDLE OUTGOING INFORMATION
            self.interactor.set_out_if_in("progress_status", "Training")
            self.interactor.set_out_if_in("progress", (curr_steps, total_steps))
            should_continue &= True
        elif self.simulation.sm.state == "<<val>>":
            self.interactor.set_out_if_in("progress_status", "Validating")
            should_continue &= True
        elif self.simulation.sm.state == "<<test>>":
            self.interactor.set_out_if_in("progress_status", "Testing")
            should_continue &= True
        # Always check for stop flag
        if self.interactor.set_out_if_in("stop_simulation", True):
            self.simulation.set_cancelled()
            should_continue &= False
        return should_continue
    
class MLSimulationSampleRecordCallback(MLSimulationCallback):
    def __init__(
        self,
        simulation: Simulation,
        sim_model: InferenceModel,
        inputs: Union[None,torch.Tensor,torch.utils.data.Dataset],
        media_path: str,
        step_trigger = 1,
        random_samples: int = -1,
    ):
        super().__init__(simulation)
        self.sim_model = sim_model
        self.inference_data = inputs
        self.random_samples = random_samples
        self.media_path = os.path.abspath(media_path)
        self.step_trigger = step_trigger
        # Setup output path
        if os.path.isdir(self.media_path):
            logger.warning(
                f"Overwriting existing videos at {self.media_path} folder "
                f"(try specifying a different `media_path` for the `MLSimulationSampleRecordCallback` callback if this is not desired)"
            )
        os.makedirs(self.media_path, exist_ok=True)

    @property
    def model(self):
        return self.sim_model.model
    def _generate_outputs(self):
        if self.model is None or self.inference_data is None:
            return (None, None)
        if self.random_samples <= 0:
            outputs, gt = self.sim_model.produce(self.inference_data)
            return (self.inference_data, outputs, gt)
        else:
            # self.inference_data should be an N-by-any tensor where each of
            # N is an individual sample
            # https://discuss.pytorch.org/t/torch-equivalent-of-numpy-random-choice/16146/2
            num_samples = min(self.random_samples, len(self.inference_data))
            idxs = torch.multinomial(torch.ones((num_samples,)))
            if isinstance(self.inference_data, torch.Tensor):
                inputs = torch.utils.data.TensorDataset(self.inference_data[idxs])
            elif isinstance(self.inference_data, torch.utils.data.Dataset):
                inputs = torch.utils.data.Subset(self.inference_data[idxs], idxs)
            outputs, gt = self.sim_model.produce(inputs)
            return (inputs, outputs, gt)
        
    @abstractmethod
    def create_media_savable(self, inputs, outputs, gt=None):
        pass

    @abstractmethod
    def save_media_to_folder(self, media_savable, step):
        pass

    def media_on_main_thread(self, inputs, outputs, curr_samples, gt=None):
        media = self.create_media_savable(inputs, outputs, gt)
        self.save_media_to_folder(media, curr_samples)
        
    def _on_invoke(self):
        curr_samples = self.locals.get("curr_samples", 0)
        if self.model is None:
            return True
        if  (self.step_trigger > 0 and \
            curr_samples > 0 and \
            curr_samples %self.step_trigger == 0):
        # Generate outputs upon trigger activation
            inputs, outputs, gt = self._generate_outputs()
            run_on_main_thread(self.media_on_main_thread, inputs, outputs, curr_samples, gt)
            # media = self.create_media_savable(inputs, outputs)
            # self.save_media_to_folder(media, curr_samples)
        return True
    
class MLClassifierRecordCallback(MLSimulationSampleRecordCallback):
    def __init__(self, simulation: Simulation, sim_model: InferenceModel, inputs: Union[None, Tensor], media_path: str, step_trigger=1, random_samples: int = -1):
        super().__init__(simulation, sim_model, inputs, media_path, step_trigger, random_samples)

    def create_media_savable(self, inputs:Union[torch.Tensor, torch.utils.data.Dataset], outputs, gt=None):
        num_plots = len(inputs)
        ncols = math.ceil(math.sqrt(num_plots))
        nrows = math.ceil(num_plots / ncols)
        fig, axs = plt.subplots(nrows, ncols)
        for p in range(num_plots):
            idx = p
            r = idx // ncols
            c = idx % ncols
            if isinstance(inputs, torch.Tensor):
                img_tensor = inputs[idx]
            elif isinstance(inputs, torch.utils.data.Dataset):
                img_tensor = inputs[idx][0]
            axs[r,c].set_title(f"pred: {outputs[idx].item()}")
            axs[r,c].imshow(torch.permute(img_tensor, (1, 2, 0)).cpu().numpy())
        for r in range(nrows):
            for c in range(ncols):
                axs[r,c].set_axis_off()
        if gt is not None:
            # Calc accuracy to show
            correct = (outputs == gt).type(torch.float).sum().item()
            accuracy = correct / num_plots
            fig.suptitle(f"Sample Accuracy: {accuracy*100:.1f}%")
        return fig
    def save_media_to_folder(self, media_savable:plt.Figure, step):
        fname = os.path.join(self.media_path, f"sample_{step}.png")
        media_savable.savefig(fname)
        plt.close(media_savable)

class MLSimulation(Simulation):
    def __init__(self, config: SimulationStartConfig) -> None:
        if not _has_torch:
            raise ImportError(f"Install pytorch to use example simulation {type(self)}.")

        super().__init__(config)

        self.can_rerun = True

        self.tb_tag_key_map = {
            stat_tags.TB_SCALARS: [
                "loss/train",
                "loss/val",
                "acc/val",
                "loss/train/train",
                "loss/train/val",
                "loss/val/val",
                "loss/test/test",
                "acc/train/train",
                "acc/train/val",
                "acc/val/val",
                "acc/test/test"
            ],
            stat_tags.TB_IMAGES: ["example_outputs"]
        }
        self.torch_loss_fns = {
            "L1Loss".lower(): torch.nn.L1Loss,
            "NLLLoss".lower(): torch.nn.NLLLoss,
            "PoissonNLLLoss".lower(): torch.nn.PoissonNLLLoss,
            "GaussianNLLLoss".lower(): torch.nn.GaussianNLLLoss,
            "KLDivLoss".lower(): torch.nn.KLDivLoss,
            "MSELoss".lower(): torch.nn.MSELoss,
            "BCELoss".lower(): torch.nn.BCELoss,
            "BCEWithLogitsLoss".lower(): torch.nn.BCEWithLogitsLoss,
            "HingeEmbeddingLoss".lower(): torch.nn.HingeEmbeddingLoss,
            "MultiLabelMarginLoss".lower(): torch.nn.MultiLabelMarginLoss,
            "SmoothL1Loss".lower(): torch.nn.SmoothL1Loss,
            "HuberLoss".lower(): torch.nn.HuberLoss,
            "SoftMarginLoss".lower(): torch.nn.SoftMarginLoss,
            "CrossEntropyLoss".lower(): torch.nn.CrossEntropyLoss,
            "MultiLabelSoftMarginLoss".lower(): torch.nn.MultiLabelSoftMarginLoss,
            "CosineEmbeddingLoss".lower(): torch.nn.CosineEmbeddingLoss,
            "MarginRankingLoss".lower(): torch.nn.MarginRankingLoss,
            "MultiMarginLoss".lower(): torch.nn.MultiMarginLoss,
            "TripletMarginLoss".lower(): torch.nn.TripletMarginLoss,
            "TripletMarginWithDistanceLoss".lower(): torch.nn.TripletMarginWithDistanceLoss,
            "CTCLoss".lower(): torch.nn.CTCLoss,
        }
        self.torch_optimizers = {
            "SGD".lower(): torch.optim.SGD,
            "Adam".lower(): torch.optim.Adam,
        }

    def _get_help_text(self):
        help_text = f"""
{type(self)}:

Description: Run a standard machine learning training process.

Supported Start Kwargs:
    train: (bool) Whether to run the training loop. Default= True.
    val: (bool) Whether to run a validation loop. Default= False.
    test: (bool) Whether to run a test loop. Default= False.
    inference: (bool) Whether to run in inference mode. Default= False.
    train_kwargs: (dict) Kwargs to be passed into the training loop:
        ckpt_per_epochs: (int) Number of epochs between saving model checkpoint. Values <=0 do not save checkpoints. Default= 1.
        epochs: (int) Number of training epochs. Default= 1,
        log_step: (int) Number of steps between logging values. Value<=0 does not log values. Default= 5.
        do_val: (bool) Whether to run a validation loop within the training loop. Default= True.
        val_per_steps: (int) Number of steps between validation loops during training. Negative does not validate per steps. Default= 500.
        val_per_epochs: (int) Number of epochs between validation loops during training. Negative does not validate per epochs. Default= -1.
        loss_fn: (str) Name of PyTorch (torch.nn) loss function to use. Default= CrossEntropyLoss.
        loss_fn_kwargs: (dict) Kwargs to pass into loss_fn creation. Default= {{}}
        optimizer: (str) Name of PyTorch (torch.optim) optimizer to use. Default= SGD.
        optimizer_kwargs: (dict) Kwargs to pass into optimizer creation. Default= {{"lr": 1e-3}}
    val_kwargs: (dict) Kwargs to be passed into the validation loop:
        ckpt: (int) Which number checkpoint to load for validation, starting at 1. Use -1 for latest checkpoint. Default= -1.
    test_kwargs: (dict)  Kwargs to be passed into the test loop:
        ckpt: (int) Which number checkpoint to load for validation, starting at 1. Use -1 for latest checkpoint. Default= -1.
    inference_kwargs: (dict)  Kwargs to be passed into the inference loop:
"""
        return help_text

    @abstractmethod
    def _create_model(**model_kwargs) -> nn.Module:
        pass
        
    def _create_streamers(self, kwargs: Dict[str, Any]):
        experiment_name = f"mnist"
        tb_path = os.path.join("tb", experiment_name, "train")
        if self._project_info_set:
            tb_path = os.path.join(self.sim_path, tb_path)
        image_path = os.path.join(self.sim_path, "media", "example_outputs")

        # Use StreamerRegistry to see if there is an existing Streamer with
        # the same streamer_name. In this case, the streamer_name checked is
        # just the tensorboard path (tb_path). This helps keep only one streamer
        # in charge of one tb folder.
        self.streamer.get_or_register(TensorboardStreamer(
            tb_path,
            self.tb_tag_key_map
        ))
        self.streamer.get_or_register(MediaFileStatLinker(
            "media_" + tb_path,
            [
                MediaLinkStreamableStat(
                    "example_outputs",
                    stat_tags.IMAGES,
                    image_path,
                    r"sample_[0-9]+\.png",
                    functools.partial(
                        MediaLinkStreamableStat.final_split_step_extractor,
                        split_char="_",
                        extension=".png"
                    )
                )
            ]
        ))

    def create_kwarg_defaults(self):
        return {
            "train": True,
            "val": False,
            "test": False,
            "inference": False,
            "train_kwargs": {},
            "val_kwargs": {},
            "test_kwargs": {},
            "inference_kwargs": {},
        }
    # Policy use custom policy dict or existing policy network:
    # https://stable-baselines3.readthedocs.io/en/sde/guide/custom_policy.html

    def _setup(self, **kwargs):
        kwargs = self._overwrite_new_kwargs(self.kwarg_defaults, self.config.kwargs, kwargs)

    def _get_checkpoint_path(self, folder_path: pathlib.Path, ckpt: int) -> Union[pathlib.Path, None]:
        files = os.listdir(folder_path)
        ckpt_files = [f for f in files if SimpleClassifierMLModel.TRAINING_CKPT_PATTERN.match(f)]
        if len(ckpt_files) < 1:
            return None
        if ckpt > 0:
            # Check for specific checkpoint file
            for f in ckpt_files:
                if f == SimpleClassifierMLModel.TRAINING_CKPT_FORMAT.format(ckpt):
                    return folder_path.joinpath(f)
        # Otherwise, just extract all the checkpoint values and find the largest
        max_ckpt = max(SimpleClassifierMLModel.TRAINING_CKPT_EXTRACTOR(f) for f in ckpt_files)
        return folder_path.joinpath(SimpleClassifierMLModel.TRAINING_CKPT_FORMAT.format(max_ckpt))

    def _cleanup_run(self):
        del self.model
        torch.cuda.empty_cache()
    def _run(self, **kwargs):
        kwargs = self._overwrite_new_kwargs(self.kwarg_defaults, self.config.kwargs, kwargs)

        do_train = kwargs.get("train", True)
        do_val = kwargs.get("val", False)
        do_test = kwargs.get("test", False)
        do_inference = kwargs.get("inference", False)
        train_kwargs = kwargs.get("train_kwargs", {})
        val_kwargs = kwargs.get("val_kwargs", {})
        test_kwargs = kwargs.get("test_kwargs", {})
        inference_kwargs = kwargs.get("inference_kwargs", {})

        logger.info(f"MLSimulation run kwargs: {kwargs}")
        logger.info(f"MLSimulation train={do_train}, val={do_val}, test={do_test}")

        # Train kwargs
        ckpt_per_epochs = train_kwargs.get("ckpt_per_epochs", 1)
        epochs = train_kwargs.get("epochs", 1)
        log_step = train_kwargs.get("log_step", 5)
        val_in_train = train_kwargs.get("do_val", True)
        val_per_steps = train_kwargs.get("val_per_steps", 500)
        val_per_epochs = train_kwargs.get("val_per_epochs", -1)
        loss_fn = train_kwargs.get("loss_fn", None)
        loss_fn = self.torch_loss_fns.get(loss_fn, self.torch_loss_fns["CrossEntropyLoss".lower()])
        loss_fn_kwargs = train_kwargs.get("loss_fn_kwargs", {})
        optimizer = train_kwargs.get("optimizer", None)
        optimizer = self.torch_loss_fns.get(optimizer, self.torch_optimizers["SGD".lower()])
        optimizer_kwargs = train_kwargs.get("optimizer_kwargs", {"lr": 1e-3})

        # Val kwargs
        val_ckpt_num = val_kwargs.get("ckpt", -1)
        # Test kwargs
        test_ckpt_num = test_kwargs.get("ckpt", -1)
        
        if (do_train):
            pass
            if (do_val):
                pass
        if (do_test):
            pass

        if (do_inference):
            # Begin inference loop, waiting for inference inputs and returning
            # processed values.
            pass

        experiment_name = f"mnist"
        tb_path = os.path.join("tb", experiment_name, "train")
        if self._project_info_set:
            tb_path = os.path.join(self.sim_path, tb_path)
        image_path = os.path.join(self.sim_path, "media", "example_outputs")

        # Setup Dataset/DataLoader
        dataset_folder_path = os.path.join(self._project_resources_path, constants.DATASET_FOLDER)
        train_path = os.path.join(dataset_folder_path, "train")
        test_path = os.path.join(dataset_folder_path, "test")
        pathlib.Path(train_path).mkdir(parents=True, exist_ok=True)
        pathlib.Path(test_path).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created folder: {train_path}")
        logger.info(f"Created folder: {test_path}")

        # Setup Checkpoint Folder
        ckpt_folder = pathlib.Path(self.sim_path, "checkpoints", "train")
        ckpt_folder.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created folder: {ckpt_folder}")

        # Use StreamerRegistry to see if there is an existing Streamer with
        # the same streamer_name. In this case, the streamer_name checked is
        # just the tensorboard path (tb_path). This helps keep only one streamer
        # in charge of one tb folder.
        self.streamer.get_or_register(TensorboardStreamer(
            tb_path,
            self.tb_tag_key_map
        ))
        self.streamer.get_or_register(MediaFileStatLinker(
            "media_" + tb_path,
            [
                MediaLinkStreamableStat(
                    "example_outputs",
                    stat_tags.IMAGES,
                    image_path,
                    r"sample_[0-9]+\.png",
                    functools.partial(
                        MediaLinkStreamableStat.final_split_step_extractor,
                        split_char="_",
                        extension=".png"
                    )
                )
            ]
        ))

        # Setup Model
        # self.model = ClassifierMNIST()
        internal_model = ClassifierMNIST()
        self.model = SimpleClassifierMLModel(ClassifierMNIST())
        self.model.add_callback("train", "start", lambda: self.sm.push_state("<<train>>"))
        self.model.add_callback("val", "start", lambda: self.sm.push_state("<<val>>"))
        self.model.add_callback("test", "start", lambda: self.sm.push_state("<<test>>"))
        self.model.add_callback("all", "end", lambda: self.sm.pop_state())

        # Get the dataset
        val_set_size = 10000
        val_split_generator = torch.Generator().manual_seed(42)
        train_data = datasets.MNIST(
            root=train_path,
            train=True,
            download=True,
            transform=ToTensor(),
        )
        train_data, val_data = torch.utils.data.random_split(train_data, [len(train_data)-val_set_size, val_set_size], val_split_generator)
        # train_data, val_data = torch.utils.data.random_split(torch.utils.data.Subset(train_data, range(6000)), [5000, 1000], val_split_generator)
        test_data = datasets.MNIST(
            root=test_path,
            train=False,
            download=True,
            transform=ToTensor(),
        )
        # train_loader = DataLoader(torch.utils.data.Subset(train_data, torch.arange(0,3000)), 32)
        train_loader = DataLoader(train_data, 32)
        val_loader = DataLoader(val_data, 32, shuffle=False)
        test_loader = DataLoader(test_data, 32, shuffle=False)

        
        step_callback = CallbackCustomList([
            MLSimulationUpdateCallback(self),
            MLClassifierRecordCallback(
                self,
                self.model,
                torch.utils.data.Subset(train_data, torch.arange(0,16)),
                image_path,
                100,
            )
        ])

        just_stopped: bool = False

        # Attempt Training
        try:
            if do_train:
                self.model.train(
                    dataloader=train_loader,
                    epochs=epochs,
                    tb_logger=tb_path,
                    log_step=log_step,
                    loss_fn=loss_fn(**loss_fn_kwargs),
                    optimizer=optimizer(self.model.model.parameters(), **optimizer_kwargs),
                    do_val=val_in_train,
                    val_per_steps=val_per_steps,
                    val_per_epochs=val_per_epochs,
                    val_kwargs={
                        "dataloader": val_loader,
                        "step_callback": MLSimulationUpdateCallback(self)
                    },
                    ckpt_per_epochs=ckpt_per_epochs,
                    ckpt_folder=ckpt_folder,
                    step_callback=step_callback,
                    # val_step_callback=MLSimulationUpdateCallback(self)
                )
                # train_mnist_classifier(self.model, dataset_folder_path, **train_kwargs)
                self.add_status(SimStatus(
                    code=SimStatusCode.SUCCESS,
                    details="Model successfully trained."
                ))
        except StopSimException as se:
            self.add_status(SimStatus(
                code=SimStatusCode.FAIL,
                subcode=SimStatusSubcode.STOPPED,
                details="Model training stopped."
            ))
            self._meta_failed = True
            just_stopped = True
        except Exception as e:
            logger.error(e)
            self._meta_failed = True
            just_stopped = True
            self.add_error_details(str(e))
        if just_stopped:
            self._cleanup_run()
            return
        
        # Attempt Validation
        try:
            if do_val:
                ckpt_path = self._get_checkpoint_path(ckpt_folder, val_ckpt_num)
                if ckpt_path is not None:
                    model_state = torch.load(ckpt_path)
                    self.model.model.load_state_dict(model_state)
                    logger.info(f"Loaded model from '{ckpt_path}' for validation.")
                    results = self.model.validate(
                        dataloader=val_loader,
                        loss_fn=loss_fn(**loss_fn_kwargs),
                        step_callback=MLSimulationUpdateCallback(self),
                        tb_logger=tb_path,
                    )
                    logger.info(f"Validation results= {results}")
                    self.add_status(SimStatus(
                        code=SimStatusCode.SUCCESS,
                        details="Model validation complete."
                    ))
                else:
                    self.add_status(SimStatus(
                        code=SimStatusCode.INFO,
                        subcode=SimStatusSubcode.NONE,
                        details="Unable to validate model with no checkpoints."
                    ))
        except StopSimException as se:
            self.add_status(SimStatus(
                code=SimStatusCode.FAIL,
                subcode=SimStatusSubcode.STOPPED,
                details="Model validation stopped."
            ))
            self._meta_failed = True
            just_stopped = True
        except Exception as e:
            logger.error(e)
            self._meta_failed = True
            just_stopped = True
            self.add_error_details(str(e))
        if just_stopped:
            self._cleanup_run()
            return

        # Attempt Testing
        try:
            if do_test:
                ckpt_path = self._get_checkpoint_path(ckpt_folder, val_ckpt_num)
                if ckpt_path is not None:
                    model_state = torch.load(ckpt_path)
                    self.model.model.load_state_dict(model_state)
                    logger.info(f"Loaded model from '{ckpt_path}' for testing.")
                    results = self.model.test(
                        dataloader=test_loader,
                        loss_fn=loss_fn(**loss_fn_kwargs),
                        step_callback=MLSimulationUpdateCallback(self),
                        tb_logger=tb_path,
                    )
                    logger.info(f"Test results= {results}")
                    self.add_status(SimStatus(
                        code=SimStatusCode.SUCCESS,
                        details="Model testing complete."
                    ))
                else:
                    self.add_status(SimStatus(
                        code=SimStatusCode.INFO,
                        subcode=SimStatusSubcode.NONE,
                        details="Unable to test model with no checkpoints."
                    ))
        except StopSimException as se:
            self.add_status(SimStatus(
                code=SimStatusCode.FAIL,
                subcode=SimStatusSubcode.STOPPED,
                details="Model testing stopped."
            ))
            self._meta_failed = True
            just_stopped = True
        except Exception as e:
            logger.error(e)
            self._meta_failed = True
            just_stopped = True
            self.add_error_details(str(e))

        self._cleanup_run()
        return

def register_example_simulations():
    SimulationRegistry.register("stable_baselines", StableBaselinesSimulation)
    SimulationRegistry.register("custom_control", CustomControlSimulation)
    SimulationRegistry.register("example_ml", MLSimulation)