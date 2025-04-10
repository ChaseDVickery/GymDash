import logging
import os
import pickle
import importlib.util
import types
import sys

import argparse
from src.gymdash.start import start

import gymnasium as gym
from stable_baselines3.common.logger import TensorBoardOutputFormat, configure
from stable_baselines3.ppo import PPO

from src.gymdash.backend.core.api.models import SimulationStartConfig
from src.gymdash.backend.core.api.stream import StreamerRegistry
from src.gymdash.backend.core.simulation import Simulation, SimulationRegistry
from src.gymdash.backend.gymnasium.wrappers.RecordVideoToTensorboard import \
    RecordVideoToTensorboard
from src.gymdash.backend.gymnasium.wrappers.TensorboardStreamWrapper import \
    TensorboardStreamWrapper
from src.gymdash.backend.stable_baselines.callbacks import \
    SimulationInteractionCallback

logger = logging.getLogger("simulation")
logger.setLevel(logging.DEBUG)

class StableBaselinesSimulation(Simulation):
    def __init__(self, config: SimulationStartConfig) -> None:
        super().__init__(config)

    def _setup(self):
        logger.info(f"setup {type(self)}")
        # self._check_kwargs_required(
        #     ["model", "run_args"],
        #     "setup",
        #     **kwargs
        # )
        # self.model = kwargs.model
        # self.run_args = kwargs.run_args

    def _run(self):
        logger.info(f"run {type(self)}")
        # self._check_kwargs_required(
        #     ["model"],
        #     "run",
        #     **kwargs
        # )

        config = self.config

        kwargs = config.kwargs



        # env_name = config.sim_type
        env_name = "CartPole-v1"



        # Check required kwargs
        self._check_kwargs_optional(["num_steps"], "init", **(config.kwargs))
        num_steps = kwargs.get("num_steps") if "num_steps" in kwargs else 5_000
        tb_path = os.path.join("tb", "cartpole", "train")

        try:
            env = gym.make(env_name, render_mode="rgb_array")
        except ValueError:
            env = gym.make(env_name)
        # Wrappers
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



if __name__ == "__main__":

    parser = argparse.ArgumentParser(
                    prog='GymDash',
                    description='Start GymDash environment and frontend',
                    epilog='Text at the bottom of help')
    parser.add_argument("-d", "--project-dir",  default=".", type=str, help="Base relative path for the GymDash project")
    parser.add_argument("-p", "--port",         default=8888, type=int, help="Port for frontend interface")
    parser.add_argument("-b", "--apiport",      default=8887, type=int, help="Port for backend API")
    parser.add_argument("-a", "--apiaddr",      default="127.0.0.1", type=str, help="Address for backend API")
    parser.add_argument("-w", "--apiworkers",   default=1, type=int, help="Number of workers for backend API")
    parser.add_argument("--apiserver",          default="dev", choices=["dev", "lan", "custom_ip"], help="How the API should be exposed. dev=only exposed to localhost (127.0.0.1). lan=local IPv4 address (usually 192.168.x.xxx). custom_ip=specify the address that the frontend should query for API access.")
    parser.add_argument("--apiserver-ip",       default="127.0.0.1", type=str, help="The custom IP address through which the API should be accessible.")
    parser.add_argument("--no-frontend",        action="store_true", help="Run without the frontend display")
    parser.add_argument("--no-backend",         action="store_true", help="Run without the backend API server")

    args = parser.parse_args()

    # SimulationRegistry.register("custom_sb_simulation", StableBaselinesSimulation)
    # print(SimulationRegistry.list_simulations())

    module_name = "custom_sb_simulation_test"
    module = types.ModuleType("custom_sb_simulation_test")
    module.StableBaselinesSimulation = StableBaselinesSimulation
    sys.modules[module_name] = module

    StableBaselinesSimulation.__module__ = module_name

    print(module.StableBaselinesSimulation.__name__)
    print(module.StableBaselinesSimulation.__module__)

    start(args, [("custom_sb_simulation", module.StableBaselinesSimulation)])