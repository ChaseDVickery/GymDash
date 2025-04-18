import logging
import os
try:
    import gymnasium as gym
    from gymnasium.wrappers import RecordVideo
    _has_gym = True
except ImportError:
    _has_gym = False
try:
    from stable_baselines3.a2c import A2C
    from stable_baselines3.common.logger import TensorBoardOutputFormat, configure
    from stable_baselines3.ddpg import DDPG
    from stable_baselines3.dqn import DQN
    from stable_baselines3.ppo import PPO
    from stable_baselines3.sac import SAC
    from stable_baselines3.td3 import TD3
    _has_sb = True
except ImportError:
    _has_sb = False

from gymdash.backend.core.api.models import SimulationStartConfig
from gymdash.backend.core.api.stream import StreamerRegistry
from gymdash.backend.core.simulation.base import (Simulation)
from gymdash.backend.core.simulation.manage import SimulationRegistry

from gymdash.backend.gymnasium.wrappers.RecordVideoToTensorboard import \
    RecordVideoToTensorboard
from gymdash.backend.gymnasium.wrappers.TensorboardStreamWrapper import \
    TensorboardStreamWrapper
from gymdash.backend.stable_baselines.callbacks import \
    SimulationInteractionCallback
from gymdash.start import start
from gymdash.backend.project import ProjectManager


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

    def _to_alg_initializer(self, alg_key: str):
        return self.algs.get(alg_key, self.algs["ppo"])

    def _to_every_x_trigger(self, value):
        if isinstance(value, int):
            return lambda x: x%value==0
        else:
            return value

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

        try:
            env = gym.make(env_name, render_mode="rgb_array")
        except ValueError:
            env = gym.make(env_name)
        # Wrappers
        # Use StreamerRegistry to see if there is an existing Streamer with
        # the same streamer_name. In this case, the streamer_name checked is
        # just the tensorboard path (tb_path). This helps keep only one streamer
        # in charge of one tb folder.
        env = StreamerRegistry.get_or_register(TensorboardStreamWrapper(
                env,
                tb_path,
                ["rewards", "rollout/ep_rew_mean", "episode_video", "episode_video_thumbnail"]
            ))
        # Record every X episodes to video.
        env = RecordVideo(
            env,
            tb_path,
            episode_trigger,
            step_trigger,
            video_length=video_length,
            fps=fps,
        )
        # Also Store the video record in the tb file.
        r_env = RecordVideoToTensorboard(
            env,
            tb_path,
            episode_trigger,
            step_trigger,
            video_length=video_length, 
            fps=fps
        )
        env = r_env
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
        r_env.configure_recorder("episode_video", tb_loggers[0].writer)
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



def register_example_simulations():
    SimulationRegistry.register("stable_baselines", StableBaselinesSimulation)