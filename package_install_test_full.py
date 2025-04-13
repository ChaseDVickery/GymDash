# must use with full install

import argparse
import importlib.util
import logging
import os
import pickle
import sys
import types


from gymdash.start import add_gymdash_arguments
from gymdash.backend.core.api.models import SimulationStartConfig
from gymdash.backend.core.api.stream import StreamerRegistry
from gymdash.backend.core.simulation.base import (Simulation,
                                                 SimulationRegistry,
                                                 SimulationTracker)
from gymdash.backend.gymnasium.wrappers.RecordVideoToTensorboard import \
    RecordVideoToTensorboard
from gymdash.backend.gymnasium.wrappers.TensorboardStreamWrapper import \
    TensorboardStreamWrapper
from gymdash.backend.stable_baselines.callbacks import \
    SimulationInteractionCallback
from gymdash.start import start
from gymdash.backend.core.simulation.examples import StableBaselinesSimulation

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser = add_gymdash_arguments(parser)
    args = parser.parse_args()
    print(args)

    tracker = SimulationTracker()
    
    SimulationRegistry.register(
        "demo",
        StableBaselinesSimulation,
        SimulationStartConfig(
            name="test",
            sim_key="CartPole-v1",
            kwargs = {
                "num_steps": 5000,
                # "episode_trigger": 50
            }
        )
    )

    # Basic with registration
    # id, sim = tracker.start_sim("demo")
    # while tracker.any_running(id):
    #     pass

    # Custom
    custom_sim1 = StableBaselinesSimulation(SimulationStartConfig(
        name="test",
        sim_key="demo",
        kwargs = {
            "num_steps": 5000,
            "env": "LunarLander-v3",
        }
    ))
    custom_sim2 = StableBaselinesSimulation(SimulationStartConfig(
        name="test",
        sim_key="Acrobot-v1",
        kwargs = {
            "num_steps": 5000,
            "env": "Acrobot-v1",
            "episode_trigger": lambda x: x%2==0
        }
    ))
    tracker.start_sim(custom_sim1)
    tracker.start_sim(custom_sim2)
