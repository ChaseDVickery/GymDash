import argparse

from gymdash.backend.core.simulation.examples import StableBaselinesSimulation
from gymdash.backend.core.simulation.export import SimulationExporter
from gymdash.start import add_gymdash_arguments, start

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
                    prog='GymDash',
                    description='Start GymDash environment and frontend',
                    epilog='')
    parser = add_gymdash_arguments(parser)

    args = parser.parse_args()

    SimulationExporter.prepare_for_export("my_custom_sim", StableBaselinesSimulation)
    SimulationExporter.export_sims()

    start(args)