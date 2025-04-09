from dataclasses import dataclass

@dataclass
class SimulationRegistryEntry:
    # Family specifies the general package/namespace
    # for that 
    display_name:       str
    sim_env_family:     str
    sim_env_key:        str
    model_env_family:   str
    model_env_key:      str


class SimulationRegistry:
    pass