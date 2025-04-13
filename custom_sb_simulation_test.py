import logging
import os
import pickle
import importlib.util
import types
import sys

import argparse
from gymdash.start import start

import gymnasium as gym
from stable_baselines3.common.logger import TensorBoardOutputFormat, configure
from stable_baselines3.ppo import PPO

from gymdash.backend.core.api.models import SimulationStartConfig
from gymdash.backend.core.api.stream import StreamerRegistry
import gymdash.backend.core.simulation.base
from gymdash.backend.core.simulation.base import Simulation, SimulationRegistry
from gymdash.backend.core.simulation.export import SimulationExporter
from gymdash.backend.gymnasium.wrappers.RecordVideoToTensorboard import \
    RecordVideoToTensorboard
from gymdash.backend.gymnasium.wrappers.TensorboardStreamWrapper import \
    TensorboardStreamWrapper
from gymdash.backend.stable_baselines.callbacks import \
    SimulationInteractionCallback
from gymdash.backend.core.simulation.examples import StableBaselinesSimulation

# logger = logging.getLogger(__name__)

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

    # module_name = "custom_sb_simulation_test"
    # module = types.ModuleType("custom_sb_simulation_test")
    # module.StableBaselinesSimulation = StableBaselinesSimulation
    # sys.modules[module_name] = module

    # StableBaselinesSimulation.__module__ = module_name

    # print(module.StableBaselinesSimulation.__name__)
    # print(module.StableBaselinesSimulation.__module__)

    # SimulationExporter.prepare_for_export(StableBaselinesSimulation, StableBaselinesSimulation.__file__, module_name)
    # SimulationExporter.export_sims()
    SimulationExporter.prepare_for_export("my_custom_sim", StableBaselinesSimulation)
    SimulationExporter.export_sims()

    start(args, [("my_custom_sim", StableBaselinesSimulation)])