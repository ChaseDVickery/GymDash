from src.api.simulation import Simulation, StableBaselinesSimulation
from threading import Thread
from typing import Any, Dict, Iterable, Tuple, Union, Set
from src.api.api_models import SimulationStartConfig, SimulationInteractionModel
import logging
from uuid import uuid4, UUID
import asyncio
from collections import defaultdict

logger = logging.getLogger("simulation")
logger.setLevel(logging.DEBUG)

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
        if (config.sim_type == "CartPole-v1"):
            simulation = StableBaselinesSimulation(config)
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
        sim.interactor.reset_outgoing_channels(to_reset)

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
        sim.interactor.reset_incoming_channels(to_reset)

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

