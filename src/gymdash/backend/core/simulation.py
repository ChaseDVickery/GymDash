import asyncio
import logging
from abc import abstractmethod
from collections import defaultdict
from threading import Thread, Lock
from typing import Any, Dict, Iterable, List, Set, Tuple, Union, Callable
from uuid import UUID, uuid4

from src.gymdash.backend.core.api.models import (SimulationInteractionModel,
                                                 SimulationStartConfig)

logger = logging.getLogger("gymdash-simulation")
logging.basicConfig(
    filename="gymdash-simulation.log",
    filemode="w",
    encoding='utf-8',
    level=logging.DEBUG
)
logger.setLevel(logging.DEBUG)

class InteractorFlag:
    def __init__(self, default_status: bool=False, default_value: Any=None) -> None:
        self.default_status = default_status
        self.default_value = default_value
        self.reset()

    def reset(self):
        self.value = self.default_value
        self.triggered = self.default_status
        logger.debug(f"InteractorFlag resetting value to default value: {self.default_value}, default status: {self.default_status} (now value=({self.value}), triggered={self.triggered})")

    def trigger_with(self, new_value: Any):
        logger.debug(f"InteractorFlag setting value to new value: {new_value}")
        # traceback.print_stack()
        self.value = new_value
        self.triggered = True
    
    def consume_trigger(self):
        consumed_trigger = self.triggered
        consumed_value = self.value
        self.reset()
        return consumed_value
    
class InteractorFlagChannel:
    def __init__(self) -> None:
        self.incoming               = InteractorFlag()
        self.outgoing               = InteractorFlag()
        self._consume_in_queued     = False
        self._consume_out_queued    = False

    @property
    def has_incoming(self):
        return self.incoming.triggered
    @property
    def has_outgoing(self):
        return self.outgoing.triggered
    
    def set_in(self, value: Any): self.set_incoming(value)
    def set_out(self, value: Any): self.set_outgoing(value)
    def set_incoming(self, value: Any):
        self.incoming.trigger_with(value)
    def set_outgoing(self, value: Any):
        print(f"InteractorFlagChannel set_outgoing value to new value: {value}")
        self.outgoing.trigger_with(value)

    # def consume_immediate_in(self) -> Any:
    #     return self.incoming.consume_trigger()
    # def consume_immediate_out(self) -> Any:
    #     return self.incoming.consume_trigger()
    def get_in(self):
        self._consume_in_queued = True
        return (self.incoming.triggered, self.incoming.value)
    def get_out(self):
        self._consume_out_queued = True
        return (self.outgoing.triggered, self.outgoing.value)
    
    def set_out_if_in(self, out_value: Any):
        """
        Triggers outgoing flag and sets its value if the incoming
        flag has been triggered. Treated as an incoming access, and
        consumption of incoming flag is queued.

        Returns:
            True if the outgoing value was set.
            False if the outgoing value was not set.
        """
        if (self.has_incoming):
            print(f"InteractorFlagChannel set_out_if_in: value={out_value}")
            self._consume_in_queued = True
            self.set_outgoing(out_value)
            return True
        return False
    def set_in_if_out(self, in_value: Any):
        """
        Triggers incoming flag and sets its value if the outgoing
        flag has been triggered. Treated as an outgoing access, and
        consumption of outgoing flag is queued.
        
        Returns:
            True if the incoming value was set.
            False if the incoming value was not set.
        """
        if (self.has_outgoing):
            self._consume_out_queued = True
            self.set_incoming(in_value)
            return True
        return False
    def set_out_if_in_value(self, out_value: Any, comparison_value: Any):
        """
        Triggers outgoing flag and sets its value if the incoming
        flag has been triggered AND the incoming value matches the comparison.
        Treated as an incoming access, and consumption of incoming
        flag is queued.
        
        Returns:
            True if the outgoing value was set.
            False if the outgoing value was not set.
        """
        if (self.has_incoming):
            self._consume_in_queued = True
            if self.incoming.value == comparison_value:
                self.set_outgoing(out_value)
                return True
        return False
    def set_in_if_out_value(self, in_value: Any, comparison_value: Any):
        """
        Triggers incoming flag and sets its value if the outgoing
        flag has been triggered AND the outgoing value matches the comparison.
        Treated as an outgoing access, and consumption of outgoing
        flag is queued.

        Returns:
            True if the incoming value was set.
            False if the incoming value was not set.
        """
        if (self.has_outgoing):
            self._consume_out_queued = True
            if self.outgoing.value == comparison_value:
                self.set_incoming(in_value)
                return True
        return False

    def reset(self):
        self.reset_outgoing()
        self.reset_incoming()
    def reset_outgoing(self):
        self.outgoing.reset()
    def reset_incoming(self): 
        self.incoming.reset()

    # def update(self):
    #     self.incoming.consume_trigger()
    #     self.outgoing.consume_trigger()
    #     self._consume_in_queued = False
    #     self._consume_out_queued = False


class SimulationInteractor:
    ALL_CHANNELS: Set[str] = set((
        "stop_simulation",
        "progress",
    ))

    def __init__(self) -> None:
        # self.stop_simulation = InteractorFlagChannel()
        # self.progress = InteractorFlagChannel()
        self.channels: Dict[str, InteractorFlagChannel] = {
            channel_key:  InteractorFlagChannel() for channel_key in SimulationInteractor.ALL_CHANNELS
        }
        self._channel_locks: Dict[str, Lock] = {
            channel_key:  Lock() for channel_key in SimulationInteractor.ALL_CHANNELS
        }
        self.triggered_in   = []
        self.triggered_out  = []

    @property
    def outgoing(self):
        return { channel_key: channel for channel_key, channel in self.channels.items() if channel.outgoing.triggered }
    @property
    def incoming(self):
        return { channel_key: channel for channel_key, channel in self.channels.items() if channel.incoming.triggered }
    
    def _aquire_all_locks(self):
        for lock in self._channel_locks.values():
            lock.acquire()
    def _release_all_locks(self):
        for lock in self._channel_locks.values():
            lock.release()
    def _aquire_locks(self, channel_keys: Iterable[str]):
        for key in channel_keys:
            self._channel_locks[key].acquire()
    def _release_locks(self, channel_keys: Iterable[str]):
        for key in channel_keys:
            self._channel_locks[key].release()
    def _aquire(self, channel_key: str):
        self._channel_locks[channel_key].acquire()
    def _release(self, channel_key: str):
        self._channel_locks[channel_key].release()
            

    # def update(self):
    #     for channel in self.channels.values():
    #         channel.update()
    def reset(self):
        self._aquire_all_locks()
        for channel in self.channels.values():
            channel.reset()
        self._release_all_locks()
    def reset_outgoing_channels(self, channel_keys: Iterable[str]):
        for key in channel_keys:
            if key in self.channels:
                self._aquire(key)
                self.channels[key].reset_outgoing()
                self._release(key)
    def reset_incoming_channels(self, channel_keys: Iterable[str]):
        for key in channel_keys:
            if key in self.channels:
                self._aquire(key)
                self.channels[key].reset_incoming()
                self._release(key)

    def _try_get_channel(self, key):
        if key in self.channels:
            return (True, self.channels[key])
        else:
            return (False, None)

    def get_in(self, channel_key):
        found, channel = self._try_get_channel(channel_key)
        return channel.get_in() if found else (False, None)
        
    def get_out(self, channel_key):
        found, channel = self._try_get_channel(channel_key)
        return channel.get_out() if found else (False, None)
    
    def get_all_outgoing_values(self) -> Dict[str, Any]:
        values = {}
        for channel_key, channel in self.channels.items():
            if channel.outgoing.triggered:
                _, value = channel.get_out()
                values[channel_key] = value
        return values
    def get_all_incoming_values(self) -> Dict[str, Any]:
        values = {}
        for channel_key, channel in self.channels.items():
            if channel.incoming.triggered:
                _, value = channel.get_in()
                values[channel_key] = value
        return values
    
    def set_out(self, channel_key: str, out_value: Any):
        found, channel = self._try_get_channel(channel_key)
        if found:
            self._aquire(channel_key)
            channel.set_out(out_value)
            self._release(channel_key)
            
    def set_in(self, channel_key: str, in_value: Any):
        found, channel = self._try_get_channel(channel_key)
        if found:
            self._aquire(channel_key)
            channel.set_in(in_value)
            self._release(channel_key)
            
    def set_out_if_in(self, channel_key: str, out_value: Any) -> bool:
        found, channel = self._try_get_channel(channel_key)
        if found:
            self._aquire(channel_key)
            was_set = channel.set_out_if_in(out_value)
            self._release(channel_key)
            return was_set
        else:
            return False
    def set_in_if_out(self, channel_key: str, in_value: Any) -> bool:
        found, channel = self._try_get_channel(channel_key)
        if found:
            self._aquire(channel_key)
            was_set = channel.set_in_if_out(in_value)
            self._release(channel_key)
            return was_set
        else:
            return False
    def set_out_if_in_value(self, channel_key: str, out_value: Any, comparison: Any):
        found, channel = self._try_get_channel(channel_key)
        if found:
            self._aquire(channel_key)
            was_set = channel.set_out_if_in_value(out_value, comparison)
            self._release(channel_key)
            return was_set
        else:
            return False
    def set_in_if_out_value(self, channel_key: str, in_value: Any, comparison: Any):
        found, channel = self._try_get_channel(channel_key)
        if found:
            self._aquire(channel_key)
            was_set = channel.set_in_if_out_value(in_value, comparison)
            self._release(channel_key)
            return was_set
        else:
            return False
        

class Simulation():
    def __init__(self, config: SimulationStartConfig) -> None:
        self.config = config
        self.thread: Thread = None
        self.start_kwargs = None
        self.interactor = SimulationInteractor()

    @property
    def is_done(self):
        return not self.thread.is_alive()

    def _check_kwargs_required(self, req_args: List[str], method_name, **kwargs):
        for arg in req_args:
            if arg not in kwargs:
                logger.error(f"Argument '{arg}' not provided for method '{method_name}' of {type(self)}")
                raise ValueError(f"Argument '{arg}' not provided for method '{method_name}' of {type(self)}")
    def _check_kwargs_optional(self, req_args: List[str], method_name, **kwargs):
        for arg in req_args:
            if arg not in kwargs:
                logger.warning(f"Argument '{arg}' not provided for method '{method_name}' of {type(self)}")

    def start(self, **kwargs):
        self.start_kwargs = kwargs
        self.setup()
        self.thread = Thread(target=self.run)
        self.thread.start()
        return self.thread

    def reset_interactions(self):
        self.interactor.reset()

    def get_outgoing_values(self) -> Dict[str, Any]:
        return self.interactor.get_all_outgoing_values()

    # def trigger_as_query(self, incoming_interactions: SimulationInteractionModel) -> Dict[str, Any]:
    #     for channel_key, value in incoming_interactions:
    #         self.interactor.set_in(channel_key, value)

    @abstractmethod
    def setup(self):
        raise NotImplementedError

    @abstractmethod
    def run(self) -> None:
        raise NotImplementedError
    
    def close(self) -> None:
        pass


class SimulationRegistry:

    registered = {}

    @staticmethod
    def register(key: str, creator: Callable[[SimulationStartConfig], Simulation]):
        print(f"HERHEHEHERHERHERHERH: {key}")
        if key in SimulationRegistry.registered:
            print(f"Cannot register simulation at key '{key}' because \
                           it is already registered.")
            logger.warning(f"Cannot register simulation at key '{key}' because \
                           it is already registered.")
            return
        print(f"Registering simulation at '{key}'")
        logger.info(f"Registering simulation at '{key}'")
        SimulationRegistry.registered[key] = creator


    @staticmethod
    def make(key: str, start_config: SimulationStartConfig):
        if key not in SimulationRegistry.registered:
            logger.error(f"Cannot make simulation at key '{key}' because it is \
                         not currently registered")
            return None
        return SimulationRegistry.registered[key](start_config)
    
    @staticmethod
    def list_simulations() -> List[str]:
        return list(SimulationRegistry.registered.keys())


class SimulationTracker:

    no_id = UUID('{00000000-0000-0000-0000-000000000000}')

    def __init__(self) -> None:
        self.running_sim_map:           Dict[UUID, Simulation] = {}
        self.done_sim_map:              Dict[UUID, Simulation] = {}
        self._current_needed_outgoing:  Dict[UUID, Dict[UUID, Set[str]]] = defaultdict(dict)
        self._current_needed_incoming:  Dict[UUID, Dict[UUID, Set[str]]] = defaultdict(dict)
        self._fullfilling_query:        bool = False
        self._fullfilling_post:         bool = False

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
        
    def is_valid(self, sim_key: Union[str, UUID]) -> bool:
        return self._to_key(sim_key) != SimulationTracker.no_id
    def is_invalid(self, sim_key: Union[str, UUID]) -> bool:
        return not self.is_valid(sim_key)
    def is_running(self, sim_key: Union[str, UUID]) -> bool:
        sim_key = self._to_key(sim_key)
        return sim_key in self.running_sim_map
    def is_done(self, sim_key: Union[str, UUID]) -> bool:
        sim_key = self._to_key(sim_key)
        return sim_key in self.done_sim_map
    
    def start_sim(self, config: SimulationStartConfig) -> Tuple[UUID, Simulation]:
        new_id = uuid4()
        logger.info(f"Attempting to start simulation (key='{new_id}', family='{config.sim_family}', type='{config.sim_type}')")
        # Create a new simulation object
        # Setup the simulation object
        # Run the simulation object
        print(SimulationRegistry.list_simulations())
        simulation = SimulationRegistry.make(config.sim_type, config)
        if simulation is not None:
            simulation.start()
            self.add_running_sim(new_id, simulation)
            logger.info(f"Started simulation (key='{new_id}', family='{config.sim_family}', type='{config.sim_type}')")
            return (new_id, simulation)
        
        logger.info(f"Could not start simulation (key='{new_id}', family='{config.sim_family}', type='{config.sim_type}')")
        return (SimulationTracker.no_id, None)

    def add_running_sim(
        self,
        sim_key: Union[str, UUID],
        sim: Simulation,
    ):
        sim_key = self._to_key(sim_key)
        if sim_key in self.running_sim_map:
            raise ValueError(f"Already running simulation for key '{sim_key}'")
        self.running_sim_map[sim_key] = sim

    def purge_finished_sims(self):
        to_remove = []
        for sim_key, sim in self.running_sim_map.items():
            if sim.is_done:
                to_remove.append(sim_key)
        self.remove_sims(to_remove)

    def remove_sims(self, to_remove: Iterable[Union[str, UUID]]) -> None:
        for sim_key in to_remove:
            sim_key = self._to_key(sim_key)
            exists, sim = self.try_get_sim(sim_key)
            if exists:
                sim.close()
                self.running_sim_map.pop(sim_key)
                self.done_sim_map[sim_key] = sim

    def try_get_sim(self, sim_key: Union[str, UUID]) -> Tuple[bool, Union[Simulation, None]]:
        sim_key = self._to_key(sim_key)
        if sim_key in self.running_sim_map:
            return (True, self.running_sim_map[sim_key])
        elif sim_key in self.done_sim_map:
            return (True, self.done_sim_map[sim_key])
        else:
            return (False, None)
    def get_sim(self, sim_key: Union[str, UUID]) -> Union[Simulation, None]:
        sim_key = self._to_key(sim_key)
        if sim_key in self.running_sim_map:
            return self.running_sim_map[sim_key]
        elif sim_key in self.done_sim_map:
            return self.done_sim_map[sim_key]
        return None
    
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
        sim_key = self._to_key(sim_key)
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
        sim_key = self._to_key(sim_key)
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
        interaction_id = uuid4()
        logger.info(f"Attempting to fulfill query interaction (interaction: {str(interaction_id)}): {sim_query}")
        query       = sim_query
        id          = self._to_key(query.id)
        timeout     = query.timeout
        can_timeout = query.timeout > 0
        found, sim  = self.try_get_sim(id)

        if not found:
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

        return response_data

    # async def fulfill_post_interaction(self, sim_query: SimulationInteractionModel):

    def send_interactions(self, sim_key, interactions: Dict[str, Any]):
        """Send interactions"""
        pass