import csv
import json
import os
import time
from glob import glob
from typing import Any, Optional, SupportsFloat, Union, Dict, List

from collections.abc import Callable

from .StatLog import StatLog

import gymnasium as gym
import pandas
from gymnasium.core import ActType, ObsType

# Similar to https://stable-baselines3.readthedocs.io/en/master/_modules/stable_baselines3/common/monitor.html#Monitor
class LogTrainingInfoWrapper(gym.Wrapper):

    # gymdash log 
    EXT = "gymdashlog.log"

    def __init__(self, env: gym.Env, filename: str = "", override_existing: bool = True):
        super().__init__(env)
        self.episode_logs:  Dict[str, StatLog]  = {
            "rewards":          StatLog(),
        }
        self.step_logs:     Dict[str, StatLog]  = {
            "rewards":          StatLog(),
        }
        self._per_episode_step_logs: Dict[str, StatLog] = {
            "rewards":          StatLog(),
        }

        self.results_writer = None
        if filename is not None:
            env_id = env.spec.id if env.spec is not None else None
            self.results_writer = ResultsWriter(
                filename,
                header={},
                extra_keys=(("rewards",)),
                # header={"t_start": self.t_start, "env_id": str(env_id)},
                # extra_keys=reset_keywords + info_keywords,
                override_existing=override_existing,
            )

    def reset(self, **kwargs) -> tuple[Any, dict[str, Any]]:
        return self.env.reset(**kwargs)
    
    def render(self):
        return self.env.render()
    
    def close(self):
        return self.env.close()

    def step(self, action: Any) -> tuple[Any, SupportsFloat, bool, bool, dict[str, Any]]:
        observation, reward, terminated, truncated, info = self.env.step(action)

        step_reward = float(reward)
        self._per_episode_step_logs
        self.step_logs["rewards"].append(step_reward)
        self._per_episode_step_logs["rewards"].append(step_reward)
        if terminated or truncated:
            self.needs_reset = True
            self.episode_logs["rewards"].append(sum(self._per_episode_step_logs["rewards"]))
            self.results_writer.write_row({"rewards": sum(self._per_episode_step_logs["rewards"])})
            self._clear_per_episode_logs()

        return observation, reward, terminated, truncated, info
    
    def _clear_per_episode_logs(self):
        for statlog in self._per_episode_step_logs.values():
            statlog.reset()



    # def _extract_step_info(self, key:str, value_transform:Callable=None, default_value=None):
    #     self._extract_info(self.step_logs, key, value_transform, default_value)
    # def _extract_episode_info(self, key:str, value_transform:Callable=None, default_value=None):
    #     self._extract_info(self.episode_logs, key, value_transform, default_value)

    # def _extract_info(self, infos:Dict[str, StatLog], key:str, value_transform:Callable=None, default_value=None):
    #     if (key not in infos):
    #         infos[key] = StatLog()
    #     found, extracted_value = self._try_extract_info(key, value_transform, default_value)
    #     if (found):
    #         infos[key].append(extracted_value)

    # def _try_extract_info(self, key:str, value_transform:Callable=None, default_value=None):
    #     value = self.locals.get(key)
    #     if (value is not None):
    #         return True, value_transform(value) if value_transform is not None else value
    #     else:
    #         return False, default_value
            
# Taken from Monitor implementation:
# https://stable-baselines3.readthedocs.io/en/master/_modules/stable_baselines3/common/monitor.html#Monitor
class ResultsWriter:
    """
    A result writer that saves the data
    """

    def __init__(
        self,
        filename: str = "",
        header: Optional[dict[str, Union[float, str]]] = None,
        extra_keys: tuple[str, ...] = (),
        override_existing: bool = True,
    ):
        if header is None:
            header = {}
        if not filename.endswith(LogTrainingInfoWrapper.EXT):
            if os.path.isdir(filename):
                filename = os.path.join(filename, LogTrainingInfoWrapper.EXT)
            else:
                filename = filename + "." + LogTrainingInfoWrapper.EXT
        filename = os.path.realpath(filename)
        # Create (if any) missing filename directories
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        # Append mode when not overriding existing file
        mode = "w" if override_existing else "a"
        # Prevent newline issue on Windows, see GH issue #692
        self.file_handler = open(filename, f"{mode}t", newline="\n")
        # self.logger = csv.DictWriter(self.file_handler, fieldnames=("r", "l", "t", *extra_keys))
        self.logger = csv.DictWriter(self.file_handler, fieldnames=(*extra_keys,))
        if override_existing:
            self.file_handler.write(f"#{json.dumps(header)}\n")
            self.logger.writeheader()

        self.file_handler.flush()

    def write_row(self, epinfo: dict[str, float]) -> None:
        """
        Write row of monitor data to csv log file.

        :param epinfo: the information on episodic return, length, and time
        """
        if self.logger:
            self.logger.writerow(epinfo)
            self.file_handler.flush()

    def close(self) -> None:
        """
        Close the file handler
        """
        self.file_handler.close()

def get_monitor_files(path: str) -> list[str]:
    """
    get all the monitor files in the given path

    :param path: the logging folder
    :return: the log files
    """
    return glob(os.path.join(path, "*" + LogTrainingInfoWrapper.EXT))

def load_results(path: str) -> pandas.DataFrame:
    """
    Load all Monitor logs from a given directory path matching ``*monitor.csv``

    :param path: the directory path containing the log file(s)
    :return: the logged data
    """
    monitor_files = get_monitor_files(path)
    if len(monitor_files) == 0:
        raise FileExistsError(f"No monitor files of the form *{LogTrainingInfoWrapper.EXT} found in {path}")
    data_frames, headers = [], []
    for file_name in monitor_files:
        with open(file_name) as file_handler:
            first_line = file_handler.readline()
            assert first_line[0] == "#"
            header = json.loads(first_line[1:])
            data_frame = pandas.read_csv(file_handler, index_col=None)
            headers.append(header)
            data_frame["t"] += header["t_start"]
        data_frames.append(data_frame)
    data_frame = pandas.concat(data_frames)
    data_frame.sort_values("t", inplace=True)
    data_frame.reset_index(inplace=True)
    data_frame["t"] -= min(header["t_start"] for header in headers)
    return data_frame