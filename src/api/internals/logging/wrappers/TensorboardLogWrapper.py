# import csv
# import json
# import os
# import time
# from glob import glob
# from typing import Any, Optional, SupportsFloat, Union, Dict, List
# from tensorboard.backend.event_processing import event_accumulator, tag_types

# from collections.abc import Callable

# from ..StatLog import StatLog
# from ..streamables.StreamableStat import StreamableStat
# from ..streamables.TensorboardStreamableStat import TensorboardStreamableStat
# from ..streamables.StreamerRegistry import StreamerRegistry
# from src.api.internals.logging.streamables.Streamer import Streamer

# import gymnasium as gym
# import pandas
# from gymnasium.core import ActType, ObsType

# class TensorboardLogWrapper(gym.Wrapper):
#     def __init__(self, env: gym.Env, filename: str = "", override_existing: bool = True):
#         super().__init__(env)
#         self.episode_logs:  Dict[str, StatLog]  = {
#             "rewards":          StatLog(),
#         }
#         self.step_logs:     Dict[str, StatLog]  = {
#             "rewards":          StatLog(),
#         }
#         self._per_episode_step_logs: Dict[str, StatLog] = {
#             "rewards":          StatLog(),
#         }

#         self.results_writer = None
#         if filename is not None:
#             env_id = env.spec.id if env.spec is not None else None
#             self.results_writer = ResultsWriter(
#                 filename,
#                 header={},
#                 extra_keys=(("rewards",)),
#                 # header={"t_start": self.t_start, "env_id": str(env_id)},
#                 # extra_keys=reset_keywords + info_keywords,
#                 override_existing=override_existing,
#             )

#     def reset(self, **kwargs) -> tuple[Any, dict[str, Any]]:
#         return self.env.reset(**kwargs)
    
#     def render(self):
#         return self.env.render()
    
#     def close(self):
#         return self.env.close()

#     def step(self, action: Any) -> tuple[Any, SupportsFloat, bool, bool, dict[str, Any]]:
#         observation, reward, terminated, truncated, info = self.env.step(action)

#         step_reward = float(reward)
#         self._per_episode_step_logs
#         self.step_logs["rewards"].append(step_reward)
#         self._per_episode_step_logs["rewards"].append(step_reward)
#         if terminated or truncated:
#             self.needs_reset = True
#             self.episode_logs["rewards"].append(sum(self._per_episode_step_logs["rewards"]))
#             self.results_writer.write_row({"rewards": sum(self._per_episode_step_logs["rewards"])})
#             self._clear_per_episode_logs()

#         return observation, reward, terminated, truncated, info
    
#     def _clear_per_episode_logs(self):
#         for statlog in self._per_episode_step_logs.values():
#             statlog.reset()