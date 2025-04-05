

import os
from typing import Callable, Union
from gymnasium import Env, error, logger
from gymnasium.wrappers import RecordVideo
from torch.utils.tensorboard import SummaryWriter
import torch as th
import numpy as np


class RecordVideoToTensorboard(RecordVideo):
    def __init__(self, env: Env, video_folder: str, episode_trigger: Union[Callable[[int], bool], None] = None, step_trigger: Union[Callable[[int], bool], None] = None, video_length: int = 0, name_prefix: str = "rl-video", fps: Union[int, None] = None, disable_logger: bool = True):
        super().__init__(env, video_folder, episode_trigger, step_trigger, video_length, name_prefix, fps, disable_logger)
        self.logger = None
        self.tag = None

    def configure_recorder(self, tag, writer):
        self.tag = tag
        self._set_summary_writer(writer)

    def _set_summary_writer(self, writer):
        self.logger: SummaryWriter = writer

    def stop_recording(self):
        """Stop current recording and saves the video into Tensorboard logger."""
        assert self.recording, "stop_recording was called, but no recording was started"
        assert self.logger, "stop_recording was called, but no SummaryWriter set to log"

        if len(self.recorded_frames) == 0:
            logger.warn("Ignored saving a video as there were zero frames to save.")
        else:
            # print(self.recorded_frames)
            # Rearrange recorded frames to format: (# vids, # frames, # channels, height, width)
            frame_stack = np.expand_dims(np.transpose(np.stack(self.recorded_frames, axis=0), axes=[0, 3, 1, 2]), axis=0)
            vid_tensor = th.from_numpy(frame_stack)
            print(f"Adding video tensor: {vid_tensor.shape}")
            # self.logger.add_video(self.tag, vid_tensor, self.episode_id, fps=30)
            self.logger.add_video(self.tag, vid_tensor, self.episode_id, fps=30)
                
            # try:
            #     from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
            # except ImportError as e:
            #     raise error.DependencyNotInstalled(
            #         'MoviePy is not installed, run `pip install "gymnasium[other]"`'
            #     ) from e

            # clip = ImageSequenceClip(self.recorded_frames, fps=self.frames_per_sec)
            # moviepy_logger = None if self.disable_logger else "bar"
            # path = os.path.join(self.video_folder, f"{self._video_name}.mp4")
            # clip.write_videofile(path, logger=moviepy_logger)

        self.recorded_frames = []
        self.recording = False
        self._video_name = None