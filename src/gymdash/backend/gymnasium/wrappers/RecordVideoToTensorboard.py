
import logging
from typing import Callable, Union

import numpy as np

try:
    from gymnasium import Env, logger
    from gymnasium.wrappers import RecordVideo
    _has_gym = True
except ImportError:
    _has_gym = False
    
try:
    from torch.utils.tensorboard import SummaryWriter
    _has_tensorboard = True
except ImportError:
    _has_tensorboard = False
    
try:
    import torch as th
    _has_torch = True
except:
    _has_torch = False
    

if not _has_gym:
    raise ImportError("Install gymnasium to use gymdash environment wrappers.")
if not _has_tensorboard:
    raise ImportError("Install tensorboard to use gymdash environment wrappers.")
if not _has_torch:
    raise ImportError("Install torch to use gymdash environment wrappers.")

logger = logging.getLogger(__name__)

class RecordVideoToTensorboard(RecordVideo):
    def __init__(self, env: Env, video_folder: str, episode_trigger: Union[Callable[[int], bool], None] = None, step_trigger: Union[Callable[[int], bool], None] = None, video_length: int = 0, name_prefix: str = "rl-video", fps: Union[int, None] = None, disable_logger: bool = True):
        super().__init__(env, video_folder, episode_trigger, step_trigger, video_length, name_prefix, fps, disable_logger)
        self.logger: SummaryWriter  = None
        self.tag: str               = None

    def configure_recorder(self, tag: str, writer: SummaryWriter):
        self.tag = tag
        self._set_summary_writer(writer)

    def _set_summary_writer(self, writer: SummaryWriter):
        self.logger = writer

    def stop_recording(self):
        """Stop current recording and saves the video into Tensorboard logger."""
        assert self.recording, "stop_recording was called, but no recording was started"
        assert self.logger, "stop_recording was called, but no SummaryWriter set to log"

        if len(self.recorded_frames) == 0:
            logger.warn("Ignored saving a video as there were zero frames to save.")
        else:
            # Rearrange recorded frames to format: (# vids, # frames, # channels, height, width)
            frame_stack = np.expand_dims(np.transpose(np.stack(self.recorded_frames, axis=0), axes=[0, 3, 1, 2]), axis=0)
            vid_tensor = th.from_numpy(frame_stack)
            # Video
            logger.info(f"Adding video tensor: {vid_tensor.shape}")
            self.logger.add_video(self.tag, vid_tensor, self.step_id, fps=30)
            # self.logger.add_video(self.tag, vid_tensor, self.episode_id, fps=30)
            # Thumbnail
            logger.info(f"Adding video thumbnail tensor: {vid_tensor[0, 0, :, :, :].shape}")
            self.logger.add_image(self.tag+"_thumbnail", vid_tensor[0, 0, :, :, :], self.step_id)
            # self.logger.add_image(self.tag+"_thumbnail", vid_tensor[0, 0, :, :, :], self.episode_id)

        self.recorded_frames = []
        self.recording = False
        self._video_name = None