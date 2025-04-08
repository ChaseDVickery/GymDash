from abc import abstractmethod
from threading import Thread
from typing import Any, Dict, Iterable, Mapping, List, Callable, Set
from src.api.api_models import SimulationStartConfig
from src.api.internals.logging.wrappers.LogTrainingInfoWrapper import LogTrainingInfoWrapper
from src.api.internals.logging.wrappers.TensorboardStreamWrapper import TensorboardStreamWrapper
from src.api.internals.logging.wrappers.RecordVideoToTensorboard import RecordVideoToTensorboard
from src.api.internals.logging.streamables.StreamerRegistry import StreamerRegistry
import os
from stable_baselines3.ppo import PPO
import gymnasium as gym
import logging
from stable_baselines3.common.logger import configure, TensorBoardOutputFormat
from stable_baselines3.common.callbacks import BaseCallback
import traceback

logger = logging.getLogger("simulation")


class InteractorFlag:
    def __init__(self, default_status: bool=False, default_value: Any=None) -> None:
        self.default_status = default_status
        self.default_value = default_value
        self.reset()

    def reset(self):
        self.value = self.default_value
        self.triggered = self.default_status
        print(f"InteractorFlag resetting value to default value: {self.default_value}")

    def trigger_with(self, new_value: Any):
        print(f"InteractorFlag setting value to new value: {new_value}")
        # traceback.print_stack()
        self.value = new_value
        self.triggered = True
    
    def consume_trigger(self):
        consumed_trigger = self.triggered
        consumed_value = self.value
        self.reset()
        return consumed_value
    
class InteractorFlagChannel:
    def __init__(self) -> None:
        self.incoming               = InteractorFlag()
        self.outgoing               = InteractorFlag()
        self._consume_in_queued     = False
        self._consume_out_queued    = False

    @property
    def has_incoming(self):
        return self.incoming.triggered
    @property
    def has_outgoing(self):
        return self.incoming.triggered
    
    def set_in(self, value: Any): self.set_incoming(value)
    def set_out(self, value: Any): self.set_outgoing(value)
    def set_incoming(self, value: Any):
        self.incoming.trigger_with(value)
    def set_outgoing(self, value: Any):
        print(f"InteractorFlagChannel set_outgoing value to new value: {value}")
        self.outgoing.trigger_with(value)
    # def consume_incoming(self) -> None:
    #     return self.incoming.consume_trigger()
    # def consume_outgoing(self) -> None:
    #     return self.incoming.consume_trigger()

    def consume_immediate_in(self) -> Any:
        return self.incoming.consume_trigger()
    def consume_immediate_out(self) -> Any:
        return self.incoming.consume_trigger()
    def get_in(self):
        self._consume_in_queued = True
        return (self.incoming.triggered, self.incoming.value)
    def get_out(self):
        self._consume_out_queued = True
        return (self.outgoing.triggered, self.outgoing.value)
    
    def set_out_if_in(self, out_value: Any):
        """
        Triggers outgoing flag and sets its value if the incoming
        flag has been triggered. Treated as an incoming access, and
        consumption of incoming flag is queued.

        Returns:
            True if the outgoing value was set.
            False if the outgoing value was not set.
        """
        if (self.has_incoming):
            print(f"InteractorFlagChannel set_out_if_in: value={out_value}")
            self._consume_in_queued = True
            self.set_outgoing(out_value)
            return True
        return False
    def set_in_if_out(self, in_value: Any):
        """
        Triggers incoming flag and sets its value if the outgoing
        flag has been triggered. Treated as an outgoing access, and
        consumption of outgoing flag is queued.
        
        Returns:
            True if the incoming value was set.
            False if the incoming value was not set.
        """
        if (self.has_outgoing):
            self._consume_out_queued = True
            self.set_incoming(in_value)
            return True
        return False
    def set_out_if_in_value(self, out_value: Any, comparison_value: Any):
        """
        Triggers outgoing flag and sets its value if the incoming
        flag has been triggered AND the incoming value matches the comparison.
        Treated as an incoming access, and consumption of incoming
        flag is queued.
        
        Returns:
            True if the outgoing value was set.
            False if the outgoing value was not set.
        """
        if (self.has_incoming):
            self._consume_in_queued = True
            if self.incoming.value == comparison_value:
                self.set_outgoing(out_value)
                return True
        return False
    def set_in_if_out_value(self, in_value: Any, comparison_value: Any):
        """
        Triggers incoming flag and sets its value if the outgoing
        flag has been triggered AND the outgoing value matches the comparison.
        Treated as an outgoing access, and consumption of outgoing
        flag is queued.

        Returns:
            True if the incoming value was set.
            False if the incoming value was not set.
        """
        if (self.has_outgoing):
            self._consume_out_queued = True
            if self.outgoing.value == comparison_value:
                self.set_incoming(in_value)
                return True
        return False

    def reset(self):
        self.reset_outgoing()
        self.reset_incoming()
    def reset_outgoing(self): self.outgoing.reset()
    def reset_incoming(self): self.incoming.reset()

    def update(self):
        self.incoming.consume_trigger()
        self.outgoing.consume_trigger()
        self._consume_in_queued = False
        self._consume_out_queued = False


class SimulationInteractor:
    ALL_CHANNELS: Set[str] = set((
        "stop_simulation",
        "progress",
    ))

    def __init__(self) -> None:
        # self.stop_simulation = InteractorFlagChannel()
        # self.progress = InteractorFlagChannel()
        self.channels: Dict[str, InteractorFlagChannel] = {
            channel_key:  InteractorFlagChannel() for channel_key in SimulationInteractor.ALL_CHANNELS
        }
        self.triggered_in   = []
        self.triggered_out  = []

    @property
    def outgoing(self):
        return { channel_key: channel for channel_key, channel in self.channels.items() if channel.outgoing.triggered }
    @property
    def incoming(self):
        return { channel_key: channel for channel_key, channel in self.channels.items() if channel.incoming.triggered }

    def update(self):
        for channel in self.channels.values():
            channel.update()
    def reset(self):
        for channel in self.channels.values():
            channel.reset()
    def reset_outgoing_channels(self, channel_keys: Iterable[str]):
        for key in channel_keys:
            if key in self.channels:
                self.channels[key].reset_outgoing()
    def reset_incoming_channels(self, channel_keys: Iterable[str]):
        for key in channel_keys:
            if key in self.channels:
                self.channels[key].reset_incoming()

    def _try_get_channel(self, key):
        if key in self.channels:
            return (True, self.channels[key])
        else:
            return (False, None)

    def get_in(self, channel_key):
        found, channel = self._try_get_channel(channel_key)
        return channel.get_in() if found else (False, None)
        
    def get_out(self, channel_key):
        found, channel = self._try_get_channel(channel_key)
        return channel.get_out() if found else (False, None)
    
    def get_all_outgoing_values(self) -> Dict[str, Any]:
        values = {}
        for channel_key, channel in self.channels.items():
            if channel.outgoing.triggered:
                _, value = channel.get_out()
                values[channel_key] = value
        return values
    def get_all_incoming_values(self) -> Dict[str, Any]:
        values = {}
        for channel_key, channel in self.channels.items():
            if channel.incoming.triggered:
                _, value = channel.get_in()
                values[channel_key] = value
        return values
    
    def set_out(self, channel_key: str, out_value: Any):
        found, channel = self._try_get_channel(channel_key)
        if found: channel.set_out(out_value)
    def set_in(self, channel_key: str, in_value: Any):
        found, channel = self._try_get_channel(channel_key)
        if found: channel.set_in(in_value)
    def set_out_if_in(self, channel_key: str, out_value: Any):
        found, channel = self._try_get_channel(channel_key)
        return channel.set_out_if_in(out_value) if found else False
    def set_in_if_out(self, channel_key: str, in_value: Any):
        found, channel = self._try_get_channel(channel_key)
        return channel.set_in_if_out(in_value) if found else False
    def set_out_if_in_value(self, channel_key: str, out_value: Any, comparison: Any):
        found, channel = self._try_get_channel(channel_key)
        return channel.set_out_if_in_value(out_value, comparison) if found else False
    def set_in_if_out_value(self, channel_key: str, in_value: Any, comparison: Any):
        found, channel = self._try_get_channel(channel_key)
        return channel.set_in_if_out_value(in_value, comparison) if found else False
        

class Simulation():
    def __init__(self, config: SimulationStartConfig) -> None:
        self.config = config
        self.thread: Thread = None
        self.start_kwargs = None
        self.interactor = SimulationInteractor()

    @property
    def is_done(self):
        return not self.thread.is_alive()

    def _check_kwargs_required(self, req_args: List[str], method_name, **kwargs):
        for arg in req_args:
            if arg not in kwargs:
                logger.error(f"Argument '{arg}' not provided for method '{method_name}' of {type(self)}")
                raise ValueError(f"Argument '{arg}' not provided for method '{method_name}' of {type(self)}")
    def _check_kwargs_optional(self, req_args: List[str], method_name, **kwargs):
        for arg in req_args:
            if arg not in kwargs:
                logger.warning(f"Argument '{arg}' not provided for method '{method_name}' of {type(self)}")

    def start(self, **kwargs):
        self.start_kwargs = kwargs
        self.setup()
        self.thread = Thread(target=self.run)
        self.thread.start()
        return self.thread

    def reset_interactions(self):
        self.interactor.reset()

    def get_outgoing_values(self) -> Dict[str, Any]:
        return self.interactor.get_all_outgoing_values()

    # def trigger_as_query(self, incoming_interactions: SimulationInteractionModel) -> Dict[str, Any]:
    #     for channel_key, value in incoming_interactions:
    #         self.interactor.set_in(channel_key, value)

    @abstractmethod
    def setup(self):
        raise NotImplementedError

    @abstractmethod
    def run(self) -> None:
        raise NotImplementedError
    
    def close(self) -> None:
        pass


class SimulationInteractionCallback(BaseCallback):
    def __init__(self, simulation_interactor: SimulationInteractor, verbose: int = 0):
        super().__init__(verbose)
        self.interactor = simulation_interactor
        
        self.curr_timesteps = 0
        self.total_timesteps = 0

    # def consume_interactors(self) -> None:
    #     self.interactor.consume_triggers()

    def _on_training_start(self) -> None:
        # From the ProgressBarCallback
        self.total_timesteps = self.locals["total_timesteps"] - self.model.num_timesteps

    def _on_rollout_start(self) -> None:
        pass

    def _on_step(self) -> bool:
        # HANDLE OUTGOING INFORMATION
        # Return progress value equivalent to the one used in ProgressBarCallback
        self.curr_timesteps += self.training_env.num_envs
        self.interactor.set_out_if_in("progress", (self.curr_timesteps, self.total_timesteps))
        # HANDLE INCOMING INFORMATION
        if self.interactor.get_in("stop_simulation")[0]:
            return False
        return True

    def _on_rollout_end(self) -> None:
        pass

    def _on_training_end(self) -> None:
        pass
    

class StableBaselinesSimulation(Simulation):
    def __init__(self, config: SimulationStartConfig) -> None:
        super().__init__(config)

    def setup(self, **kwargs):
        logger.info(f"setup {type(self)}")
        # self._check_kwargs_required(
        #     ["model", "run_args"],
        #     "setup",
        #     **kwargs
        # )
        # self.model = kwargs.model
        # self.run_args = kwargs.run_args

    def run(self):
        logger.info(f"run {type(self)}")
        # self._check_kwargs_required(
        #     ["model"],
        #     "run",
        #     **kwargs
        # )

        config = self.config

        kwargs = config.kwargs

        env_name = config.sim_type
        # Check required kwargs
        self._check_kwargs_optional(["num_steps"], "init", **(config.kwargs))
        num_steps = kwargs.get("num_steps") if "num_steps" in kwargs else 5_000
        tb_path = os.path.join("tb", "cartpole", "train")

        try:
            env = gym.make(env_name, render_mode="rgb_array")
        except ValueError:
            env = gym.make(env_name)
        # Wrappers
        env = LogTrainingInfoWrapper(env, "testout")
        env = StreamerRegistry.get_or_register(TensorboardStreamWrapper(
                env,
                tb_path,
                ["rewards", "rollout/ep_rew_mean", "episode_video", "episode_video_thumbnail"]
            ))
        r_env = RecordVideoToTensorboard(env, tb_path, lambda x: x%100==0, video_length=0, fps=30)
        env = r_env
        # Callbacks
        sim_interact_callback = SimulationInteractionCallback(self.interactor)
        # Logger
        backend_logger = configure(tb_path, ["tensorboard"])

        # Setup Model
        self.model = PPO("MlpPolicy", env, verbose=0, tensorboard_log=tb_path)
        self.model.set_logger(backend_logger)
        tb_loggers = [t for t in self.model.logger.output_formats if isinstance(t, TensorBoardOutputFormat)]
        print(tb_loggers)
        r_env.configure_recorder("episode_video", tb_loggers[0].writer)

        self.model.learn(total_timesteps=num_steps, progress_bar=True, callback=sim_interact_callback)
        self.model.save("ppo_aapl")