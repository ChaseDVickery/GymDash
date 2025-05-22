# use with either basic or full install

import argparse
import time
import functools
import uuid
import logging
from typing import List

from gymdash.backend.project import ProjectManager
from gymdash.backend.core.api.models import SimulationStartConfig
from gymdash.backend.core.simulation.base import Simulation
from gymdash.backend.core.simulation.manage import SimulationTracker, SimulationRegistry
from gymdash.start import add_gymdash_arguments


class DemoSimulation(Simulation):
    def __init__(self, config: SimulationStartConfig) -> None:
        super().__init__(config)
        self.runtime = None
        self.polltime = 0
        self._timer = 0
        self.result = None
        self.show_timer = True

    def _setup(self):
        self._check_kwargs_required(
            ["sim_time", "poll_time"],
            "setup",
            **self.config.kwargs
        )
        self.runtime = self.config.kwargs["sim_time"]
        self.polltime = self.config.kwargs["poll_time"]
        self.timer = 0
        self.show_timer = self.config.kwargs["show_timer"] if "show_timer" in self.config.kwargs is not None else True
        self.result = None

    def _run(self) -> None:
        while (self.timer < self.runtime):
            time.sleep(self.polltime)
            if self.show_timer:
                print(f"{self.timer:.2f}/{self.runtime:.2f}")
            self.timer += self.polltime
        self.result = f"DemoSimulation({self.runtime}, {self.polltime}) \
                        completed successfully."
        
def create_demo_sim():
    return DemoSimulation(SimulationStartConfig(
        name="test",
        sim_key="test",
        kwargs = {
            "sim_time": 2,
            "poll_time": 0.5
        }
    ))

def print_on_done(sim: DemoSimulation):
    print(sim.result)
def print_on_all_done(simulations: List[DemoSimulation]):
    print("All the simulations are done. Here I repeat their resulting outputs:")
    for sim in simulations:
        print(sim.result)
def print_on_all_done2():
    print("Hooray! All done still!")


def compare_direct_vs_group(tracker: SimulationTracker):
    num_sims = 10
    num_trials = 10
    print("------------------------------------------------------")
    print(f"Starting direct-manipulation trials")
    direct_trials = []
    for i in range(num_trials):
        st = time.time()
        ids = []
        for _ in range(num_sims):
            id, _ = tracker.start_sim("demo")
            ids.append(id)
        while(tracker.any_running(ids)):
            pass
        et = time.time()
        direct_trials.append(et - st)
    direct_time = sum(direct_trials)
    avg_direct_time = direct_time / num_trials
    avg_direct_time_per_sim = avg_direct_time / num_sims
    print(f"Done with direct-manipulation trials.\n")

    # SimulationGroups
    print("------------------------------------------------------")
    print(f"Starting group-manipulation trials")
    group_trials = []
    for i in range(num_trials):
        st = time.time()
        sim_group = tracker.start_sims(["demo" for _ in range(num_sims)])
        while(sim_group.any_running):
            pass
        et = time.time()
        group_trials.append(et - st)
    group_time = sum(group_trials)
    avg_group_time = group_time / num_trials
    avg_group_time_per_sim = avg_group_time / num_sims
    print(f"Done with group-manipulation trials.")
    print("------------------------------------------------------")
    print(f"Results:")
    print(f"Direct:")
    print(f"\tTotal Time: {direct_time:.2f}s")
    print(f"\tAvg Time:   {avg_direct_time:.2f}s")
    print(f"\tSims/s:     {(num_sims*num_trials/direct_time):.2f}")
    print(f"Group:")
    print(f"\tTotal Time: {group_time:.2f}")
    print(f"\tAvg Time:   {avg_group_time:.2f}")
    print(f"\tSims/s:     {(num_sims*num_trials/group_time):.2f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser = add_gymdash_arguments(parser)
    args = parser.parse_args()
    print(args)

    ProjectManager.setup_from_args(args)

    tracker = SimulationTracker()
    

    # Running simulation takes 2 seconds
    print("------------------------------------------------------")
    print(f"Starting demo simulation on main thread")
    testsim = create_demo_sim()
    st = time.time()
    testsim.setup()
    testsim.run()
    et = time.time()
    print(testsim.result)
    print(f"Demo simulation finished after {et-st:.2f}s")

    # Handle multiple simulations
    print("------------------------------------------------------")
    print(f"Starting 2 simulations in SimulationTracker")
    sim1 = create_demo_sim()
    sim2 = create_demo_sim()
    st = time.time()
    id1, _ = tracker.start_sim(sim1)
    id2, _ = tracker.start_sim(sim2)
    while tracker.any_running(id1) or tracker.any_running(id2):
        pass
    et = time.time()
    print(sim1.result)
    print(sim2.result)
    print(f"Simulations finished after {et-st:.2f}s")


    # Handle a bunch of simulations
    num_sims = 9
    print("------------------------------------------------------")
    print(f"Starting {num_sims} simulations with specific handling.")
    sims: List[Simulation] = []
    st = time.time()
    for i in range(num_sims):
        sim = create_demo_sim()
        id, _ = tracker.start_sim(sim)
        sim.runtime = 1 + (i//3)
        sim.show_timer = False
        sims.append(sim)
    done = False
    while(not done):
        for i in range(len(sims)-1, -1, -1):
            if sims[i].is_done:
                print(sims.pop(i).result)
        if len(sims) == 0:
            done = True
    et = time.time()
    print(f"Done with all {num_sims} sims.")
    print(f"Simulations finished after {et-st:.2f}s")


    # Handle with a done-callback
    num_sims = 9
    print("------------------------------------------------------")
    print(f"Starting {num_sims} simulations with callback handling")
    ids: List[uuid.UUID] = []
    sims: List[Simulation] = []
    st = time.time()
    for i in range(num_sims):
        sim = create_demo_sim()
        id, _ = tracker.start_sim(sim)
        # sim.add_callback(Simulation.END_RUN, functools.partial(print_on_done, sim=sim))
        sim.add_callback(Simulation.END_RUN, functools.partial(
            lambda sim: print(sim.result), sim=sim
        ))
        sim.show_timer = False
        ids.append(id)
        sims.append(sim)
    # group_callback_id = tracker.on_all_done(ids, functools.partial(print_on_all_done, simulations=sims))
    group_callback_id = tracker.on_all_done(ids, functools.partial(
        lambda simulations: list(map(lambda s: print(s.result), sims)), simulations=sims
    ))
    # tracker.add_on_all_done(group_callback_id, print_on_all_done2)
    tracker.add_on_all_done(group_callback_id, lambda: print("Hooray! All done!"))
    while(tracker.any_running(ids)):
        pass
    et = time.time()
    print(f"Done with all {num_sims} sims.")
    print(f"Simulations finished after {et-st:.2f}s")


    # Basic usage with registration
    # Register
    num_sims = 10
    print("------------------------------------------------------")
    print(f"Starting {num_sims} simulation with registered simulation")
    default_config = SimulationStartConfig(
        name="demo",
        sim_key="demo",
        kwargs = {
            "sim_time": 2,
            "poll_time": 0.1,
            "show_timer": False
        }
    )
    SimulationRegistry.register("demo", DemoSimulation, default_config)
    # Use
    ids = []
    sims = []
    st = time.time()
    for i in range(num_sims):
        id, sim = tracker.start_sim("demo")
        ids.append(id)
        sims.append(sim)
    # def p(toprint):
    #     for a in toprint:
    #         print(a.result)
    # tracker.on_all_done(ids, functools.partial(p, toprint=sims))
    while(tracker.any_running(ids)):
        pass
    et = time.time()
    print(f"Done with all {num_sims} sims.")
    print(f"Simulations finished after {et-st:.2f}s")


    # SimulationGroups
    num_sims = 10
    print("------------------------------------------------------")
    print(f"Starting {num_sims} simulations with SimulationGroup")
    st = time.time()
    sim_group = tracker.create_simulations(["demo" for _ in range(num_sims)])
    sim_group.add_on_all_run_start(lambda: print("All sims started"))
    # for sim in sim_group.sims:
    #     sim.add_callback(Simulation.END_RUN, functools.partial(print_on_done, sim=sim))
    sim_group.sims[-1].add_callback(Simulation.END_RUN, functools.partial(print_on_done, sim=sim_group.sims[-1]))
    sim_group.add_on_all_run_end(lambda: print("All sims ended"))
    tracker.start_sims(sim_group)
    while(sim_group.any_running):
        pass
    et = time.time()
    print(f"Done with all {num_sims} sims.")
    print(f"Simulations finished after {et-st:.2f}s")

    compare_direct_vs_group(tracker)
