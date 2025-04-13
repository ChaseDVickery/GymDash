import logging
import os
import pickle
import importlib.util
import types
import sys

import argparse
from gymdash.start import start, add_gymdash_arguments

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
    parser = add_gymdash_arguments(parser)

    args = parser.parse_args()

    SimulationExporter.prepare_for_export("my_custom_sim", StableBaselinesSimulation)
    SimulationExporter.export_sims()

    start(args)