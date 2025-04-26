import asyncio
import functools
import logging
from collections import defaultdict
from datetime import datetime
from threading import Lock
from typing import Any, Callable, Dict, Iterable, List, Set, Tuple, Union
from uuid import UUID, uuid4
import queue

from gymdash.backend.core.api.models import (InteractorChannelModel,
                                             SimulationInteractionModel,
                                             SimulationStartConfig,
                                             StoredSimulationInfo)
from gymdash.backend.core.simulation.base import Simulation
from gymdash.backend.project import ProjectManager
from gymdash.backend.core.utils.type_utils import get_type

logger = logging.getLogger(__name__)

class SimulationRegistry:

    registered: Dict[
        str, 
        Tuple[Callable[[SimulationStartConfig], Simulation], Union[SimulationStartConfig, None]]
    ] = {}

    @staticmethod
    def register(
        key: str,
        creator: Callable[[SimulationStartConfig], Simulation],
        default_config: Union[SimulationStartConfig, None] = None
    ) -> None:
        """
        Adds the Simulation initializer and optional default configuration
        to the registration map if provided key is not already used.

        Args:
            key: Registered name of the simulation type to register
            creator: Initializer/type of the Simulation to register
            start_config: Optional default configuration
        """
        if key in SimulationRegistry.registered:
            logger.warning(f"Cannot register simulation at key '{key}' because \
                           it is already registered.")
            return
        logger.info(f"Registering simulation at '{key}'")
        SimulationRegistry.registered[key] = (creator, default_config)


    @staticmethod
    def make(key: str, start_config: Union[SimulationStartConfig, None] = None):
        """
        Instantiate and return a Simulation at the provided key
        using either the provided configuration or the default
        configuration specified during registration if none was
        passed in.

        Args:
            key: Registered name of the simulation type to start
            start_config: Optional start configuration
        Returns:
            New Simulation instance if success, None if failure.
        """
        if key not in SimulationRegistry.registered:
            logger.error(f"Cannot make simulation at key '{key}' because it is \
                         not currently registered")
            return None
        creator = SimulationRegistry.registered[key][0]
        config = SimulationRegistry.registered[key][1]
        start_config = start_config if start_config is not None else config
        if start_config is None:
            logger.error(f"Cannot make simulation at key '{key}' becayse it needs\
                         at least a default config or a config passed into make()\
                         as an argument")
            return None
        return creator(start_config)
    
    @staticmethod
    def list_simulations() -> List[str]:
        """Returns a list of registered Simulation keys."""
        return list(SimulationRegistry.registered.keys())
    
class TriggeredCallback:
    def __init__(self, num_req_triggers: int = 1) -> None:
        self._callbacks:    List[Callable]  = []
        self._req_triggers: int             = num_req_triggers
        self._num_triggers: int             = 0
        self.activated:     bool            = False

    def add_callback(self, callback: Callable):
        self._callbacks.append(callback)

    def trigger(self, increment: int = 1):
        self._num_triggers += increment
        if (self._num_triggers >= self._req_triggers):
            self.activate()

    def activate(self):
        self.activated = True
        for callback in self._callbacks:
            callback()

class SimulationGroup:
    def __init__(
        self,
        sim_infos: List[Tuple[UUID, Simulation]]
    ) -> None:
        self.id:    UUID                            = uuid4()
        self.infos: List[Tuple[UUID, Simulation]]   = sim_infos
        self.ids:   List[UUID]                      = [info[0] for info in self.infos]
        self.sims:  List[Simulation]                = [info[1] for info in self.infos]
        # self.triggered_callbacks:   Dict[UUID, TriggeredCallback] = {}
        self.triggered_callback_all_run_start:  TriggeredCallback = TriggeredCallback(len(self.sims))
        self.triggered_callback_all_run_end:    TriggeredCallback = TriggeredCallback(len(self.sims))

        for sim in self.sims:
            sim.add_callback(Simulation.START_RUN, self.triggered_callback_all_run_start.trigger)
            sim.add_callback(Simulation.END_RUN, self.triggered_callback_all_run_end.trigger)

    @property
    def all_done(self):
        for sim in self.sims:
            if not sim.is_done:
                return False
        return True
    @property
    def any_running(self):
        return not self.all_done

    def add_on_all_run_start(self, callback: Callable) -> None:
        """
        Adds a callback to run once all simulations in the group
        have started to run.
        """
        self.triggered_callback_all_run_start.add_callback(callback)
    def add_on_all_run_end(self, callback: Callable) -> None:
        """
        Adds a callback to run once all simulations in the group
        have ended their run.
        """
        self.triggered_callback_all_run_end.add_callback(callback)
    def add_on_each_run_start(self, callback: Callable) -> None:
        """
        Adds a callback to each simulation in the group which runs
        when that simulation's run starts. Equivalent to calling
        sim.add_callback(Simulation.START_RUN, ...) on each simulation
        in the group.
        """
        for sim in self.sims:
            sim.add_callback(Simulation.START_RUN, callback)
    def add_on_each_run_end(self, callback: Callable) -> None:
        """
        Adds a callback to each simulation in the group which runs
        when that simulation's run ends. Equivalent to calling
        sim.add_callback(Simulation.END_RUN, ...) on each simulation
        in the group.
        """
        for sim in self.sims:
            sim.add_callback(Simulation.END_RUN, callback)
    

class SimulationTracker:

    no_id = UUID('{00000000-0000-0000-0000-000000000000}')

    def __init__(self) -> None:
        self.running_sim_map:           Dict[UUID, Simulation] = {}
        self.done_sim_map:              Dict[UUID, Simulation] = {}
        self._current_needed_outgoing:  Dict[UUID, Dict[UUID, Set[str]]] = defaultdict(dict)
        self._current_needed_incoming:  Dict[UUID, Dict[UUID, Set[str]]] = defaultdict(dict)
        self.queued_sims:               List[Tuple[Simulation, Dict[str,Any]]] = []

        self._access_mutex:             Lock = Lock()
        
        self._clear_poll_period:        float= 0.1
        # This flag should be true while clear() is being called.
        # We need to check this flag during fulfill_query_interaction because
        # if we start trying to clear the tracker while the current query
        # fulfillments are being processed, then they need to know to stop
        # and return immediately.
        self._is_clearing_internal:     bool = False
        # Similarly, while processing clear(), we need to be sure not to
        # finish clearing the maps if any query fulfillments are still in
        # process.
        self._current_queries:          set = set()

        # This flag just for outside use
        self._is_clearing:              bool = False

        self.callback_groups:           Dict[UUID, TriggeredCallback] = {}
        
        

        # loop = asyncio.get_event_loop()
        # loop.create_task(self.purge_loop())

    @property
    def _fullfilling_query(self):
        return len(self._current_queries) > 0
    @property
    def is_clearing(self):
        return self._is_clearing
    
    async def stop_simulation_call(self, sim_id) -> SimulationInteractionModel:
        print("STOP_SIMULATION_CALL")
        sim_id = self._to_key(sim_id)
        if (sim_id in self.running_sim_map):
            logger.info("HERE")
            # Normal call to stop sim
            results = await self.stop_simulation(sim_id)
            return results
        else:
            logger.info("THERE")
            # Check in queued simulations to remove it
            num_queued = len(self.queued_sims)
            for i in range(num_queued-1, -1, -1):
                logger.info(f"{self.queued_sims[i][0]._project_sim_id} vs {sim_id}")
                if (self.queued_sims[i][0]._project_sim_id is not None and self.queued_sims[i][0]._project_sim_id == sim_id):
                    popped = self.queued_sims.pop(i)
                    popped[0].set_cancelled()
                    # self.update_sim_dbs([sim_id])
                    ProjectManager.add_or_update_simulation(sim_id, popped[0])
                    self._set_sim_done(sim_id, popped[0])
                    return SimulationInteractionModel(
                        id=str(sim_id),
                        stop_simulation=InteractorChannelModel(triggered=True, value=""),
                        cancelled=InteractorChannelModel(triggered=popped[0]._meta_cancelled, value=""),
                    )
    
    async def stop_simulation(self, sim_id):
        if (sim_id not in self.running_sim_map):
            await asyncio.sleep(0)
        else:
            await self.fulfill_query_interaction(SimulationInteractionModel(
                id=str(sim_id),
                stop_simulation=InteractorChannelModel(triggered=True, value=None)
            ))

    async def clear(self):
        """
        Sends stop simulation query to all running simulations.
        Then clears all mappings.
        """
        self._is_clearing = True
        stop_sim_tasks = []
        stop_sim_ids = []
        with self._access_mutex:
            stop_sim_ids = [id for id in self.running_sim_map.keys()]
            for sim_id in stop_sim_ids:
                stop_sim_tasks.append(
                    asyncio.create_task(
                        self.stop_simulation(sim_id)
                        # self.fulfill_query_interaction(SimulationInteractionModel(
                        #     id=str(sim_id),
                        #     stop_simulation=InteractorChannelModel(triggered=True, value=None)
                        # ))
                    )
                )
        # Must first GATHER the stop interactions to make sure that all
        # relevant simulations have had stop called. After that, we can abort
        # other interactions early if needed.
        responses = await asyncio.gather(*stop_sim_tasks)
        # Enable clearing flag after stop_simulation calls have been registered
        # for each running simulation
        self._is_clearing_internal = True
        # Possibly wait here while other unrelated fulfillments finish up.
        # Other interactions should be checking for the _is_clearing_internal flag
        while (self._fullfilling_query):
            print(f"Waiting on {self._current_queries} query fulfillment")
            await asyncio.sleep(self._clear_poll_period)
        # Wait still for individual Simulation threads to finish.
        # We want to be sure that all simulation threads are done
        # so that we prevent them from using resources (like tb directories)
        # that may be cleared in other parts of the code after this
        # (like from ProjectManager)
        while self.any_running(stop_sim_ids):
            print(f"Waiting on simulation thread shutdowns")
            await asyncio.sleep(self._clear_poll_period)
        # Now clear out all my maps and such
        self.running_sim_map.clear()
        self.done_sim_map.clear()
        self._current_needed_outgoing.clear()
        self._current_needed_incoming.clear()
        self.callback_groups.clear()
        self.queued_sims.clear()
        self._is_clearing_internal = False
        self._is_clearing = False
        return responses
    
    async def clear_specific(self, sim_ids: List[Union[str, UUID]]):
        stop_sim_tasks = []
        stop_sim_ids = []
        with self._access_mutex:
            stop_sim_ids = [self._to_key(id) for id in sim_ids]
            for sim_id in stop_sim_ids:
                stop_sim_tasks.append(
                    asyncio.create_task(
                        self.stop_simulation(sim_id)
                    )
                )
        # Must first GATHER the stop interactions to make sure that all
        # relevant simulations have had stop called. After that, we can abort
        # other interactions early if needed.
        responses = await asyncio.gather(*stop_sim_tasks)
        # Wait still for individual Simulation threads to finish.
        # We want to be sure that all simulation threads are done
        # so that we prevent them from using resources (like tb directories)
        # that may be cleared in other parts of the code after this
        # (like from ProjectManager)
        while self.any_running(stop_sim_ids):
            print(f"Waiting on selected simulation thread shutdowns")
            await asyncio.sleep(self._clear_poll_period)
        # Now clear out all my maps and such
        for sim_id in stop_sim_ids:
            if self.running_sim_map.pop(sim_id, None) is None:
                if self.done_sim_map.pop(sim_id, None) is None:
                    # Now try to remove from queud sims if queued
                    num_queued = len(self.queued_sims)
                    for i in range(num_queued-1, -1, -1):
                        if (self.queued_sims[i][0]._project_sim_id is not None and self.queued_sims[i][0]._project_sim_id == sim_id):
                            self.queued_sims.pop(i)

        return responses
        
    def load_old_simulations_from_info(self, stored_infos: List[StoredSimulationInfo]):
        """
        Creates and stores old simulations using information stored and
        retrieved from disk. Such simulations should not already exist
        in the maps, and all such simulations should be done or forcibly
        stopped, otherwise they will not be loaded into the tracker. This
        is here so that interfacing with old data streams from other places
        will be easier because the revived simulations should automatically
        provide information necessary to reconstruct log file paths upon
        their re-instantiation.

        Args:
            stored_infos: List of simulation informations retrieved from disk.
        """
        if self.is_clearing:
            return
        with self._access_mutex:
            for sim_info in stored_infos:
                sim_id = self._to_key(sim_info.sim_id)
                sim_type = get_type(sim_info.sim_type_name, sim_info.sim_module_name)
                sim_done = sim_info.is_done
                sim_stopped = sim_info.force_stopped
                sim_start_kwargs = sim_info.start_kwargs
                # Check for simulation type
                if sim_type is None:
                    logger.error(f"Cannot load old simulation ({sim_info.sim_id}) because type ({sim_info.sim_type_name}) cannot be found.")
                    continue
                # Check for simulation ID existence
                if sim_id in self.done_sim_map:
                    logger.error(f"Cannot load old simulation ({sim_info.sim_id}) because ID is already found in the tracker's done_sim_map.")
                    continue
                if sim_id in self.running_sim_map:
                    logger.error(f"Cannot load old simulation ({sim_info.sim_id}) because ID is already found in the tracker's running_sim_map.")
                    continue
                # Check simulation doneness
                if not sim_done and not sim_stopped:
                    logger.error(f"Cannot load old simulation ({sim_info.sim_id}) because it is not marked as either done nor forcibly stopped. Simulations loaded from disk cannot still be running.")
                    continue
                # Create new sim instance from stored config.
                # Also set from_disk so we cannot accidentally run it again.
                revived_sim: Simulation = sim_type(sim_info.config)
                revived_sim.fill_from_stored_info(sim_info)
                revived_sim.set_project_info(ProjectManager.sims_folder(), revived_sim._project_sim_id)
                revived_sim.create_streamers()
                print(f"SimulationTracker adding old simulation at: {sim_id}")
                self.done_sim_map[sim_id] = revived_sim
                print(f"SimulationTracker done_sim_map: {self.done_sim_map}")


    def _to_key(self, key: Union[str, UUID]) -> UUID:
        # If UUID, we're good
        if isinstance(key, UUID):
            return key
        # If not string, convert to string
        key_str = key
        if not isinstance(key, str):
            key_str = str(key)
        # Convert string form to UUID
        try:
            uuid = UUID(key_str)
            return uuid
        except ValueError:
            return SimulationTracker.no_id
        
    @property
    def testing_first_id(self):
        if len(self.running_sim_map) < 1:
            return SimulationTracker.no_id
        else:
            # Return the first ID found by iterator
            # for running simulations
            for id in self.running_sim_map.keys():
                return id
            
    def _set_sim_running(self, sim_key: UUID, sim: Simulation):
        with self._access_mutex:
            self.running_sim_map[sim_key] = sim
    def _set_sim_done(self, sim_key: UUID, sim: Simulation):
        with self._access_mutex:
            self.done_sim_map[sim_key] = sim
    def _get_sim_internal(self, sim_key: Union[str, UUID]) -> Union[Simulation, None]:
        sim_key = self._to_key(sim_key)
        with self._access_mutex:
            if sim_key in self.running_sim_map:
                return self.running_sim_map[sim_key]
            elif sim_key in self.done_sim_map:
                return self.done_sim_map[sim_key]
            else:
                return None
    def try_get_sim(self, sim_key: Union[str, UUID]) -> Tuple[bool, Union[Simulation, None]]:
        sim = self._get_sim_internal(sim_key)
        if sim is None:
            return (False, None)
        else:
            return (True, sim)
    def get_sim(self, sim_key: Union[str, UUID]) -> Union[Simulation, None]:
        logger.debug(f"SimulationTracker done_sim_map: {self.done_sim_map}")
        return self._get_sim_internal(sim_key)
    def get_sims(self, sim_keys: List[Union[str, UUID]]) -> List[Union[Simulation, None]]:
        return [self.get_sim(key) for key in sim_keys]
    def is_valid(self, sim_key: Union[str, UUID]) -> bool:
        return self._to_key(sim_key) != SimulationTracker.no_id
    def is_invalid(self, sim_key: Union[str, UUID]) -> bool:
        return not self.is_valid(sim_key)
    def _is_done_single(self, sim_key: Union[str, UUID]) -> bool:
        sim = self.get_sim(sim_key)
        if sim is None:
            return True
        else:
            return sim.is_done
    def _is_running_single(self, sim_key: Union[str, UUID]) -> bool:
        return not self._is_done_single(sim_key)
    def all_done(self, sim_keys: Union[Union[str, UUID], List[Union[str, UUID]]]) -> bool:
        """
        Checks whether all queried simulations are done.
        Returns true if ALL simulations are done, false otherwise

        Args:
            sim_keys: Either a single or list of simulation keys.
        Returns:
            is_done: True if ALL simulations are done, False otherwise
        """
        if isinstance(sim_keys, list):
            for key in sim_keys:
                if not self._is_done_single(key):
                    return False
            return True
        else:
            return self._is_done_single(sim_keys)
    def any_running(self, sim_keys: Union[Union[str, UUID], List[Union[str, UUID]]]) -> bool:
        """
        Checks whether any queried simulations are running.
        Returns true if ANY simulations are running, false otherwise

        Args:
            sim_keys: Either a single or list of simulation keys.
        Returns:
            is_running: True if ANY simulations are running, False otherwise
        """
        return not self.all_done(sim_keys)
    
    def add_on_all_done(self, callback_group_id: UUID, callback: Callable) -> bool:
        if callback_group_id in self.callback_groups:
            self.callback_groups[callback_group_id].add_callback(callback)
            return True
        else:
            logger.warning(f"Cannot add callback to group ID '{str(callback_group_id)}'")
            return False
    def on_all_done(self, sim_keys: Union[Union[str, UUID], List[Union[str, UUID]]], callback: Callable):
        group_id = uuid4()
        if isinstance(sim_keys, list):
            triggered_callback = TriggeredCallback(len(sim_keys))
            triggered_callback.add_callback(callback)
            # Each simulation should increment the TriggeredCallback counter
            # when done, so when the last one finishes, the TriggeredCallback
            # should finally trigger
            for key in sim_keys:
                sim = self.get_sim(key)
                sim.add_callback(Simulation.END_RUN, triggered_callback.trigger)
        else:
            triggered_callback = TriggeredCallback(1)
            triggered_callback.add_callback(callback)
        self.callback_groups[group_id] = triggered_callback
        return group_id
    
    def create_simulations(self, to_create: Union[SimulationGroup,List[Union[str, SimulationStartConfig, Simulation]]]) -> SimulationGroup:
        # Return the existing group if passed in
        if isinstance(to_create, SimulationGroup):
            return to_create
        # Otherwise, create new SimulationGroup
        created = []
        for potential in to_create:
            created.append(self.create_simulation(potential))
        group = SimulationGroup(created)
        return group
    
    def create_simulation(self, to_create: Union[str, SimulationStartConfig, Simulation]) -> Tuple[UUID, Simulation]:
        new_id = uuid4()
        is_str = isinstance(to_create, str)
        is_sim = isinstance(to_create, Simulation)
        is_config = isinstance(to_create, SimulationStartConfig)
        if not is_sim and not is_config and not is_str:
            logger.warning(f"Could not create simulation because input was invalid")
            return (SimulationTracker.no_id, None)
        # Create a new simulation object or use the passed one
        if is_str:
            to_create: str = to_create
            simulation = SimulationRegistry.make(to_create)
            logger.info(f"Created simulation (type='{to_create}', id='{new_id}') with default registered config.")
        elif is_config:
            to_create: SimulationStartConfig = to_create
            simulation = SimulationRegistry.make(to_create.sim_key, to_create)
            logger.info(f"Created simulation object with config (type='{to_create.sim_key}', id='{new_id}')")
        elif is_sim:
            to_create: Simulation = to_create
            simulation = to_create
            new_id = new_id if simulation._project_sim_id is None else simulation._project_sim_id
            simulation._project_sim_id = new_id
            logger.info(f"Creating existing simulation object (id='{new_id}')")
        if simulation is None:
            logger.warning(f"Could not create valid simulation.")
            return (SimulationTracker.no_id, None)
        simulation.set_project_info(ProjectManager.sims_folder(), new_id)
        ProjectManager.add_or_update_simulation(new_id, simulation)
        return (new_id, simulation)


    def start_sims(
        self, 
        to_start: Union[SimulationGroup, List[Union[str, SimulationStartConfig, Simulation]]],
        **kwargs
    ) -> SimulationGroup:
        """
        Begins multiple simulations using a set of input kwargs.

        Args:
            to_start: List of simulations, configs, or simulation names to start.
            kwargs: Custom start kwarg overrides for all simulations.
        Returns:
            group: SimulationGroup of all started simulations.
        """
        group = self.create_simulations(to_start)
        for info in group.infos:
            sim_id = info[0]
            sim = info[1]
            # Add callbacks. Mostly to update sim db at certain points
            on_done = functools.partial(self.on_sim_done, sim_ids=[sim_id])
            on_start_setup = functools.partial(self.update_sim_dbs, sim_ids=[sim_id])
            sim.add_callback(Simulation.END_RUN, on_done)
            sim.add_callback(Simulation.START_SETUP, on_start_setup)
            # Begin simulation
            sim.start(**kwargs)
            self.add_running_sim(sim_id, sim)
            logger.info(f"Started simulation (id='{sim_id}') in group '{group.id}'")
        return group
    
    def start_sim(
        self,
        to_start: Union[str, SimulationStartConfig, Simulation],
        **kwargs
    ) -> Tuple[UUID, Simulation]:
        """
        Begins a single simulation given a simulation, config, or sim name.

        Args:
            to_start: Simulation, config, or simulation name to start.
            kwargs: Custom start kwarg overrides for the simulation.
        Returns:
            info: The started simulation ID and the simulation.
        """
        id, simulation = self.create_simulation(to_start)
        if simulation is not None:
            # Upon simulation finishing,
            # trigger its removal from running simulations
            # Add other callbacks. Mostly to update sim db at certain points/
            on_done = functools.partial(self.on_sim_done, sim_ids=[id])
            on_start_setup = functools.partial(self.update_sim_dbs, sim_ids=[id])
            simulation.add_callback(Simulation.END_RUN, on_done)
            simulation.add_callback(Simulation.START_SETUP, on_start_setup)
            # Begin simulation/
            simulation.start(**kwargs)
            self.add_running_sim(id, simulation)
            logger.info(f"Started simulation (id='{id}')")
            return (id, simulation)
        
        logger.warning(f"Could not start simulation (key='{id}')")
        return (SimulationTracker.no_id, None)
    
    def start_next_queued_sim(self) -> Tuple[UUID, Simulation]:
        if self._is_clearing:
            return (SimulationTracker.no_id, None)
        if len(self.queued_sims) > 0:
            # with self._access_mutex:
            to_start, kwargs = self.queued_sims.pop(0)
            logger.info(f"Starting queued simulation {to_start._project_sim_id}")
            logger.debug(f"Starting queued simulation {to_start._project_sim_id} with kwargs {kwargs}")
            return self.start_sim(to_start, **kwargs)

    def queue_sim(
        self,
        to_start: Union[str, SimulationStartConfig, Simulation],
        **kwargs
    ) -> Tuple[UUID, Simulation]:
        # Create new simulation with config, then queue
        # it if it was created correctly
        new_id, sim = self.create_simulation(to_start)
        if (new_id != SimulationTracker.no_id and sim is not None):
            self.queued_sims.append((
                sim,
                kwargs
            ))
        else:
            logger.warning(f"Could not queue simulation because created simulation was invalid")
        if len(self.running_sim_map) < 1 and len(self.queued_sims) > 0:
            return self.start_next_queued_sim()
        return (new_id, sim)

    def add_running_sim(
        self,
        sim_key: Union[str, UUID],
        sim: Simulation,
    ):
        sim_key = self._to_key(sim_key)
        if sim_key in self.running_sim_map:
            raise ValueError(f"Already running simulation for key '{sim_key}'")
        self._set_sim_running(sim_key, sim)

    # async def purge_loop(self):
    #     while True:
    #         await asyncio.sleep(0.1)
    #         self.purge_finished_sims()

    # def purge_finished_sims(self):
    #     to_remove = []
    #     for sim_key, sim in self.running_sim_map.items():
    #         if sim.is_done:
    #             to_remove.append(sim_key)
    #     self.remove_sims(to_remove)
        
    def on_sim_done(self, sim_ids: Iterable[Union[str, UUID]]) -> None:
        self.remove_sims(sim_ids)
        self.update_sim_dbs(sim_ids)
        # If there are not simulations left running,
        # then start a queued simulation
        if len(self.running_sim_map) < 1:
                self.start_next_queued_sim()
            
    def update_sim_dbs(self, sim_ids: Iterable[Union[str, UUID]]) -> None:
        for sim_key in sim_ids:
            key = self._to_key(sim_key)
            exists, sim = self.try_get_sim(key)
            if exists:
                ProjectManager.add_or_update_simulation(key, sim)

    def remove_sims(self, to_remove: Iterable[Union[str, UUID]]) -> None:
        for sim_key in to_remove:
            # print(f"Removing sim {sim_key}")
            exists, sim = self.try_get_sim(sim_key)
            if exists:
                sim.close()
                self.running_sim_map.pop(sim_key)
                self.done_sim_map[sim_key] = sim
    
    def _start_query(self, query_id: UUID):
        self._current_queries.add(query_id)
    def _end_query(self, query_id: UUID):
        self._current_queries.remove(query_id)

    def _reset_free_outgoing_response_triggers(self, sim_key: Union[str, UUID], just_freed: Set[str]):
        """
        Resets all outgoing channels that were just freed from an interaction
        as long as they are also not being used by any other interaction
        for the simulation.

        Args:
            sim_key: Simulation ID to which the freeing should apply.
            just_freed: Set of channel keys that was just freed after
                a completed interaction.
        """
        found, sim = self.try_get_sim(sim_key)
        if not found: return
        used = set() if len(self._current_needed_outgoing[sim_key]) < 1 else set.union(*self._current_needed_outgoing[sim_key].values())
        to_reset = just_freed.difference(used)
        logger.debug(f"SimulationTracker attempting to reset outgoing channels for {to_reset}")
        logger.debug(f"SimulationTracker pre-reset status of outgoing channels {to_reset}: {[(item[0], item[1].outgoing.triggered) for item in sim.interactor.channels.items() if item[0] in to_reset]}")
        sim.interactor.reset_outgoing_channels(to_reset)
        logger.debug(f"SimulationTracker post-reset status of outgoing channels {to_reset}: {[(item[0], item[1].outgoing.triggered) for item in sim.interactor.channels.items() if item[0] in to_reset]}")

    def _reset_free_incoming_response_triggers(self, sim_key: Union[str, UUID], just_freed: Set[str]):
        """
        Resets all incoming channels that were just freed from an interaction
        as long as they are also not being used by any other interaction
        for the simulation.

        Args:
            sim_key: Simulation ID to which the freeing should apply.
            just_freed: Set of channel keys that was just freed after
                a completed interaction.
        """
        found, sim = self.try_get_sim(sim_key)
        if not found: return
        used = set() if len(self._current_needed_outgoing[sim_key]) < 1 else set.union(*self._current_needed_outgoing[sim_key].values())
        to_reset = just_freed.difference(used)
        logger.debug(f"SimulationTracker attempting to reset incoming channels for {to_reset}")
        logger.debug(f"SimulationTracker pre-reset status of incoming channels {to_reset}: {[(item[0], item[1].incoming.triggered) for item in sim.interactor.channels.items() if item[0] in to_reset]}")
        sim.interactor.reset_incoming_channels(to_reset)
        logger.debug(f"SimulationTracker post-reset status of incoming channels {to_reset}: {[(item[0], item[1].incoming.triggered) for item in sim.interactor.channels.items() if item[0] in to_reset]}")

    async def fulfill_query_interaction(self, sim_query: SimulationInteractionModel):
        """
        Attempts to fulfill a query to a simulation by triggering incoming channels
        and polling those triggered channels for outgoing values.

        Args:
            sim_query: Query representing all channels for which information
                has been requested.
        Returns:
            response: A SimulationInteracionModel containing either responses for
                all queried channels, OR responses for only some queried channels
                if a timeout occurred, OR a response with a "no-id" simulation
                if the queried simulation could not be found.
        """
        if self._is_clearing_internal:
            logger.info(f"Query interaction returning early because of clear flag")
            return SimulationInteractionModel(id=str(SimulationTracker.no_id))
        interaction_id = uuid4()
        self._start_query(interaction_id)
        logger.info(f"Attempting to fulfill query interaction (interaction: {str(interaction_id)}).")
        logger.debug(f"Query interaction details (interaction: {str(interaction_id)}): {sim_query}")
        query       = sim_query
        id          = self._to_key(query.id)
        timeout     = query.timeout
        can_timeout = query.timeout > 0
        found, sim  = self.try_get_sim(id)

        if not found or self._is_clearing_internal:
            self._end_query(interaction_id)
            return SimulationInteractionModel(id=str(SimulationTracker.no_id))
        
        # We want to assemble a list of attributes that be checked off
        # as they resolve in each simulation and their data populates
        # our response
        needed_response_keys = set((
            channel_tuple[0] for channel_tuple in query.triggered_channels
        ))
        response_data = {}
        # Add the channels keys needed to fulfill this response to the list
        self._current_needed_outgoing[id][interaction_id] = needed_response_keys
        self._current_needed_incoming[id][interaction_id] = needed_response_keys
        # Mark needed response channels by triggering them so the simulation
        # knows to populate the outgoing channel with an update.
        for channel_key in needed_response_keys:
            sim.interactor.set_in(channel_key, True)
        
        # After marking channels for output, begin polling loop
        await asyncio.sleep(0)
        poll_period = 0.05
        done = False
        timer = 0
        while not done:
            if self._is_clearing_internal:
                self._end_query(interaction_id)
                return response_data
            retrieved_values = sim.get_outgoing_values()
            logger.debug(f"Simulation tracker retrieved outgoing values: {retrieved_values}")
            for channel_key, outgoing_value in retrieved_values.items():
                # If the outgoing key was not part of this query, then ignore it
                if channel_key not in needed_response_keys:
                    continue
                # If the outgoing key has already been logged, then do NOT overwrite it
                # with the new outgoing value. This could happen if another query
                # API request comes in at the same time this one is processing.
                if channel_key in response_data:
                    continue
                # channel_key not is a needed response and is not already logged
                # so log the response
                response_data[channel_key] = outgoing_value
            # We are done assembling our response if we time-out or if
            # we gather a full response
            done_success = len(response_data) >= len(needed_response_keys)
            done_timeout = can_timeout and timer >= timeout
            done = done_success or done_timeout
            if done_success:    logger.info(f"Query {id} (interaction: {str(interaction_id)}) successfully gathered.")
            elif done_timeout:  logger.info(f"Query {id} (interaction: {str(interaction_id)}) timed out.")
            # If not yet done, then increase our timer and wait until
            # next polling
            if not done:
                timer += poll_period
                await asyncio.sleep(poll_period)

        # Remove the channel keys needed for my response from
        # the collection of required keys for this Simulation,
        # and then try to reset any outgoing channels that are
        # now free in this Simulation.
        self._current_needed_outgoing[id].pop(interaction_id)
        self._current_needed_incoming[id].pop(interaction_id)
        self._reset_free_outgoing_response_triggers(id, needed_response_keys)
        self._reset_free_incoming_response_triggers(id, needed_response_keys)

        self._end_query(interaction_id)
        return response_data