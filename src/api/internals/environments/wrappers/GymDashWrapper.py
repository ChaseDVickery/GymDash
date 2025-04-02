from typing import Any, SupportsFloat
import gymnasium as gym



class GymDashWrapper(gym.Wrapper):
    def __init__(self, env: gym.Env):
        super().__init__(env)
        # Set new:
        # self.action_space
        # self.observation_space
        # self.metadata

    # Override step...
    # def step(self, action: Any) -> tuple[Any, SupportsFloat, bool, bool, dict[str, Any]]:
    #     return super().step(action)
    
    # Override render...
    # def render(self) -> gym.RenderFrame | list[gym.RenderFrame] | None:
    #     return super().render()
    
    # Override close...
    # def close(self):
    #     return super().close()
    