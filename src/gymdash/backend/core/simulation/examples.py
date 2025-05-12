import functools
import logging
import os
import pathlib
import time
import math
from typing import Union
from abc import abstractmethod

import matplotlib.pyplot as plt
from torch import Tensor
from torch.utils.tensorboard import SummaryWriter

import gymdash.backend.constants as constants
from gymdash.backend.core.simulation.callbacks import BaseCustomCallback, CallbackCustomList
from gymdash.backend.torch.base import (InferenceModel,
                                        SimpleClassifierMLModel,
                                        SimulationMLModel)

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
        except Exception as e:
            self._meta_failed = True
            self.add_error_details(str(e))
            pass
        env.close()


class CustomControlSimulation(Simulation):
    def __init__(self, config: SimulationStartConfig) -> None:
        if not _has_np:
            raise ImportError(f"Install numpy to use example simulation {type(self)}.")
        super().__init__(config)
        
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
    
    def handle_interactions(self):
        self.interactor.set_out_if_in("progress", (self.curr_timesteps, self.total_timesteps))
        # HANDLE INCOMING INFORMATION
        if self.interactor.set_out_if_in("stop_simulation", True):
            self.simulation.set_cancelled()
            return False
        return True

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
                # Manage pause points
                # Pause if we are at the next pause point time
                if curr_pause_point < len(pause_points) and timer >= pause_points[curr_pause_point]:
                    self.interactor.add_control_request("custom_query", "Please send custom_query with 'continue' key to continue.")
                    # Once we get a custom query with a "continue" key, then
                    # we can increment the pause point index and move on
                    while True:
                        # Handle normal
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
        should_continue = True
        if self.state == "train":
            curr_steps = self.locals.get("curr_steps", 0)
            total_steps = self.locals.get("total_steps", 1)
            # HANDLE OUTGOING INFORMATION
            self.interactor.set_out_if_in("progress", (curr_steps, total_steps))
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
            logger.warn(
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
            outputs = self.sim_model.produce(self.inference_data)
            return (self.inference_data, outputs)
        else:
            # self.inference_data should be an N-by-any tensor where each of
            # N is an individual sample
            # https://discuss.pytorch.org/t/torch-equivalent-of-numpy-random-choice/16146/2
            num_samples = min(self.random_samples, len(self.inference_data))
            idxs = torch.multinomial(torch.ones((num_samples,)))
            if isinstance(self.inference_data, torch.Tensor):
                inputs = self.inference_data[idxs]
            elif isinstance(self.inference_data, torch.utils.data.Dataset):
                inputs = torch.utils.data.Subset(self.inference_data[idxs], idxs)
            outputs = self.sim_model.produce(inputs)
            return (inputs, outputs)
        
    @abstractmethod
    def create_media_savable(self, inputs, outputs):
        pass

    @abstractmethod
    def save_media_to_folder(self, media_savable, step):
        pass
        
    def _on_invoke(self):
        curr_samples = self.locals.get("curr_samples", 0)
        if self.model is None:
            return True
        if  (self.step_trigger > 0 and \
            curr_samples > 0 and \
            curr_samples %self.step_trigger == 0):
        # Generate outputs upon trigger activation
            inputs, outputs = self._generate_outputs()
            media = self.create_media_savable(inputs, outputs)
            self.save_media_to_folder(media, curr_samples)
            
            self.sim_model.produce(self.inference_data)
        return True
    
class MLClassifierRecordCallback(MLSimulationSampleRecordCallback):
    def __init__(self, simulation: Simulation, sim_model: InferenceModel, inputs: Union[None, Tensor], media_path: str, step_trigger=1, random_samples: int = -1):
        super().__init__(simulation, sim_model, inputs, media_path, step_trigger, random_samples)

    def create_media_savable(self, inputs:Union[torch.Tensor, torch.utils.data.Dataset], outputs):
        num_plots = len(inputs)
        ncols = math.ceil(math.sqrt(num_plots))
        nrows = math.ceil(num_plots / ncols)
        fig, axs = plt.subplots(nrows, ncols)
        for p in range(num_plots):
            idx = p
            r = idx // ncols
            c = idx % ncols
            target = ""
            if isinstance(inputs, torch.Tensor):
                img_tensor = inputs[idx]
            elif isinstance(inputs, torch.utils.data.Dataset):
                img_tensor = inputs[idx][0]
                target = str(inputs[idx][1])
            axs[r,c].set_axis_off()
            axs[r,c].set_title(f"pred: {outputs[idx].item()}")
            axs[r,c].imshow(torch.permute(img_tensor, (1, 2, 0)).cpu().numpy())
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

        self.tb_tag_key_map = {
            stat_tags.TB_SCALARS: ["loss/train", "loss/val", "acc/val",],
            stat_tags.TB_IMAGES: ["example_outputs"]
        }

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

    def _run(self, **kwargs):
        kwargs = self._overwrite_new_kwargs(self.kwarg_defaults, self.config.kwargs, kwargs)
        model_kwargs = kwargs.get("model_kwargs", {})

        # self._create_model(**model_kwargs)

        do_train = kwargs.get("train", True)
        do_val = kwargs.get("val", False)
        do_test = kwargs.get("test", False)
        do_inference = kwargs.get("inference", False)
        train_kwargs = kwargs.get("train_kwargs", {})
        val_kwargs = kwargs.get("val_kwargs", {})
        test_kwargs = kwargs.get("test_kwargs", {})
        inference_kwargs = kwargs.get("inference_kwargs", {})

        # Train kwargs
        epochs = train_kwargs.get("epochs", 1)
        
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
        self.model = SimpleClassifierMLModel(ClassifierMNIST())

        # Setup Dataset/DataLoader
        dataset_folder_path = os.path.join(self._project_resources_path, constants.DATASET_FOLDER)
        train_path = os.path.join(dataset_folder_path, "train")
        test_path = os.path.join(dataset_folder_path, "test")
        pathlib.Path(train_path).mkdir(parents=True, exist_ok=True)
        pathlib.Path(test_path).mkdir(parents=True, exist_ok=True)
        # Get the dataset
        train_data = datasets.MNIST(
            root=train_path,
            train=True,
            download=True,
            transform=ToTensor(),
        )
        test_data = datasets.MNIST(
            root=train_path,
            train=False,
            download=True,
            transform=ToTensor(),
        )
        # train_loader = DataLoader(torch.utils.data.Subset(train_data, torch.arange(0,3000)), 32)
        train_loader = DataLoader(train_data, 32)
        test_loader = DataLoader(test_data, 32)

        
        step_callback = CallbackCustomList([
            MLSimulationUpdateCallback(self),
            MLClassifierRecordCallback(
                self,
                self.model,
                torch.utils.data.Subset(train_data, torch.arange(0,10)),
                image_path,
                100,
            )
        ])

        try:
            self.model.train(
                dataloader=train_loader,
                epochs=epochs,
                tb_logger=tb_path,
                log_step=5,
                do_val=True,
                val_per_epoch=1,
                val_kwargs={
                    "dataloader": test_loader
                },
                step_callback=step_callback,
            )
            # train_mnist_classifier(self.model, dataset_folder_path, **train_kwargs)
        except Exception as e:
            logger.error(e)
            self._meta_failed = True
            self.add_error_details(str(e))
            del self.model
            torch.cuda.empty_cache()
            raise e


def register_example_simulations():
    SimulationRegistry.register("stable_baselines", StableBaselinesSimulation)
    SimulationRegistry.register("custom_control", CustomControlSimulation)
    SimulationRegistry.register("example_ml", MLSimulation)