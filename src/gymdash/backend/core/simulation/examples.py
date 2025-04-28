import logging
import os
import time

from torch.utils.tensorboard import SummaryWriter

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
from typing import Any, Dict

import gymdash.backend.core.api.config.stat_tags as stat_tags
from gymdash.backend.core.api.models import SimulationStartConfig
from gymdash.backend.core.simulation.base import Simulation
from gymdash.backend.core.simulation.manage import SimulationRegistry
from gymdash.backend.gymnasium.wrappers.RecordVideoToTensorboard import \
    RecordVideoToTensorboard
from gymdash.backend.gymnasium.wrappers.TensorboardStreamWrapper import (
    TensorboardStreamer, TensorboardStreamWrapper)
from gymdash.backend.stable_baselines.callbacks import \
    SimulationInteractionCallback

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
        
    
        
    def _create_streamers(self, kwargs: Dict[str, Any]):
        experiment_name = f"{kwargs['env']}_{kwargs['algorithm']}"
        tb_path = os.path.join("tb", experiment_name, "train")
        if self._project_info_set:
            tb_path = os.path.join(self.sim_path, tb_path)
        self.streamer.get_or_register(TensorboardStreamer(
            tb_path,
            {
                stat_tags.TB_SCALARS: ["rewards", "rollout/ep_rew_mean", "train/learning_rate"],
                stat_tags.TB_IMAGES: ["episode_video", "episode_video_thumbnail"]
            }
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
                {
                    stat_tags.TB_SCALARS: ["rewards", "rollout/ep_rew_mean"],
                    stat_tags.TB_IMAGES: ["episode_video", "episode_video_thumbnail"]
                }
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



def register_example_simulations():
    SimulationRegistry.register("stable_baselines", StableBaselinesSimulation)
    SimulationRegistry.register("custom_control", CustomControlSimulation)