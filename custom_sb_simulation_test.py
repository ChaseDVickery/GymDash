import argparse
import importlib.util
import logging
import os
import pickle
import sys
import types

import gymnasium as gym
from stable_baselines3.common.logger import TensorBoardOutputFormat, configure
from stable_baselines3.ppo import PPO

import gymdash.backend.core.simulation.base
from gymdash.backend.core.api.models import SimulationStartConfig
from gymdash.backend.core.api.stream import StreamerRegistry
from gymdash.backend.core.simulation.base import Simulation
from gymdash.backend.core.simulation.examples import StableBaselinesSimulation
from gymdash.backend.core.simulation.export import SimulationExporter
from gymdash.backend.core.simulation.manage import SimulationRegistry
from gymdash.backend.gymnasium.wrappers.RecordVideoToTensorboard import \
    RecordVideoToTensorboard
from gymdash.backend.gymnasium.wrappers.TensorboardStreamWrapper import \
    TensorboardStreamWrapper
from gymdash.backend.stable_baselines.callbacks import \
    SimulationInteractionCallback
from gymdash.start import add_gymdash_arguments, start

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