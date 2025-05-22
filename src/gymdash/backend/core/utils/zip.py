import io
import json
import logging
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Union

try:
    from tensorboard.backend.event_processing.event_accumulator import (
        AudioEvent, CompressedHistogramEvent, HistogramEvent, ImageEvent,
        ScalarEvent)
    _has_tensorboard = True
except ImportError:
    _has_tensorboard = False
    


import gymdash.backend.core.api.config.stat_tags as tags
from gymdash.backend.core.api.stream import StreamerRegistry
from gymdash.backend.core.simulation.base import Simulation, SimulationStreamer
from gymdash.backend.core.utils.file_format import (FileFormat,
                                                    format_from_bytes)
from gymdash.backend.core.utils.json import DataclassJSONEncoder


from gymdash.backend.tensorboard.MediaLinkStreamableStat import FileEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MediaMetadata:
    """Contains information for an arbitrary media file represented as bytes.

    Attributes:
      mimetype: MIME type of file.
      step: The step at which the media was recorded
    """
    key: str            # stat key
    mimetype: str       # MIME type of the media
    step:   int         # step of the logged media
    wall_time: float

@dataclass(frozen=True)
class JSONMetadata:
    """Contains information for JSON-formatted data.
    Usually for a sequence of values.

    Attributes:
      mimetype: MIME type of file. Should always be 'application/json'
    """
    key: str
    mimetype: str  = "application/json"

@dataclass(frozen=True)
class ZippedMediaFile:
    streamer_key: str
    metadata: Dict[str, MediaMetadata]
    sim_id: str         = ""

@dataclass(frozen=True)
class ZippedIndex:
    streamer_key: str
    # Map types to dict mapping filenames to metadata
    metadata: Dict[str, Dict[str, Union[MediaMetadata, JSONMetadata]]]
    sim_id: str         = ""


# def tb_media_to_json(event: List[Union[ImageEvent, AudioEvent]]):
#     """Encode the event data as a JSON string and then encode that as a b64 string."""
#     return base64.b64encode(json.dumps(event))

def tb_event_to_media_format(event) -> Union[FileFormat, None]:
    """
    Return the mimetype for the contents of a media file
    logged in a tensorboard file. Returns None if no
    such event or if conversion cannot find suitable
    indicators of a particular type.
    """
    if not _has_tensorboard:
        return None
    # https://stackoverflow.com/questions/57785500/how-to-know-mime-type-of-a-file-from-base64-encoded-data-in-python
    fformat = None
    if isinstance(event, ImageEvent):
        fformat = format_from_bytes(event.encoded_image_string)
    elif isinstance(event, AudioEvent):
        fformat = format_from_bytes(event.encoded_audio_string)
    elif isinstance(event, FileEvent):
        fformat = format_from_bytes(event.encoded_string)
    return fformat

def event_to_media_format(event) -> Union[FileFormat, None]:
    fformat = None
    if _has_tensorboard:
        fformat = tb_event_to_media_format(event)
    else:
        # Finally, try to just directly guess format from event arg
        fformat = format_from_bytes(event)
    if fformat is None:
        logger.warning(f"Cannot guess event media format for type '{type(event)}'. You may need to install tensorboard.")
    return fformat

# def zips_to_zip(zips: Iterable[io.BytesIO]):
#     pass

# def pack_streamer_media_to_zip(streamer_key: str, key_event_map: Dict[str, List[Any]]):
#     """ Packs media data from a single streamer into zipped bytes.

#     Zips up media events from a streamer, creating a new file
#     from each media event. The resulting zip contains all media
#     files with relevant extensions and an index file containing
#     information mapping the streamer key and other data for each
#     media file in the zip file.

#     Args:
#         streamer_key: Name/key of the streamer sending the data
#         key_event_map: Maps stat keys to a list of events containing
#             media information that must be zipped.
#     Returns:
#         Bytes buffer of the zipped information.
#     """
#     zip_buffer = io.BytesIO()
#     with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
#         media_index = {}
#         # For each stat key, iterate all the events
#         # and write each event's associated media data to a
#         # new file in the zip
#         for key, media_events in key_event_map.items():
#             file_prefix = f"{key}_"
#             for i, event in enumerate(media_events):
#                 media_format = event_to_media_format(event)
#                 if media_format is None:
#                     raise RuntimeError(f"No valid media format found for event '{event}' in from streamer '{streamer_key}' for key '{key}'")
#                 mime_type = media_format.mime if media_format.has_mimetype else ""
#                 ext = media_format.ext if media_format.has_extension else ""
#                 filename = file_prefix + str(i) + f".{ext}"
#                 if isinstance(event, ImageEvent):
#                     zip_file.writestr(filename, event.encoded_image_string)
#                     media_index[filename] = MediaMetadata(mimetype=mime_type)
#                 elif isinstance(event, AudioEvent):
#                     zip_file.writestr(filename, event.encoded_audio_string)
#                     media_index[filename] = MediaMetadata(mimetype=mime_type)
#         # Add the index file to the zip
#         index_data = ZippedMediaFile(streamer_key, media_index)
#         zip_file.writestr("index.json", json.dumps(index_data, cls=DataclassJSONEncoder))
#     zip_buffer.seek(0)
#     return zip_buffer

# def get_recent_media_from_tag(media_tag: str):
#     if media_tag not in tags.MEDIA_TAG_SET:
#         print(f"get_recent_media tried to retrieve media from tag '{media_tag}' but it is not a media tag")
#         return {}
    
#     # dictionary containing valid results from all streamers
#     # with the key being each streamer's streamer_name/from
#     # the StreamerRegistry key
#     # Maps [streamer key -> [stat key -> List[tb event value]]]
#     streamer_responses: Dict[str, Dict[str, List[Any]]] = {}
#     for streamer_key, streamer in StreamerRegistry.items():
#         recent = streamer.get_recent_from_tag(media_tag)
#         streamer_responses[streamer_key] = {
#             key: event_values for key, event_values in recent.items() if len(event_values) > 0
#         }

#     # print(f"streamer responses: {streamer_responses}")
#     zipped = []
#     for streamer_key, key_media_responses in streamer_responses.items():
#         zip_buffer = pack_streamer_media_to_zip(streamer_key, key_media_responses)
#         zipped.append(zip_buffer)
#         with zipfile.ZipFile(zip_buffer, "r") as zip:
#             print(f"zip file for streamer '{streamer_key}': {zip.filelist}")
#             print("index: ", zip.open("index.json").read())

#     return zipped

# def get_recent_media_from_keys(keys: List[str]) -> List[io.BytesIO]:
#     # dictionary containing valid results from all streamers
#     # with the key being each streamer's streamer_name/from
#     # the StreamerRegistry key
#     # Maps [streamer key -> [stat key -> List[tb event value]]]
#     streamer_responses: Dict[str, Dict[str, List[Any]]] = defaultdict(dict)
#     for streamer_key, streamer in StreamerRegistry.items():
#         for key in keys:
#             recent = streamer.get_recent_from_key(key)
#             event_values = recent[key]
#             if len(event_values) < 1:
#                 continue
#             # streamer_responses[streamer_key] = event_values
#             streamer_responses[streamer_key][key] = event_values
#             print(f"api recent test things count: {len(event_values)}")
    
#     # print(f"streamer responses: {streamer_responses}")
#     zipped = []
#     for streamer_key, key_media_responses in streamer_responses.items():
#         zip_buffer = pack_streamer_media_to_zip(streamer_key, key_media_responses)
#         zipped.append(zip_buffer)
#         with zipfile.ZipFile(zip_buffer, "r") as zip:
#             print(f"zip file for streamer '{streamer_key}': {zip.filelist}")
#             print("index: ", zip.open("index.json").read())

#     return zipped

# def get_recent_media_generator_from_tag(media_tag: str, key: str):
#     zipped = get_recent_media_from_tag(media_tag, key)
#     for zip_buffer in zipped:
#         yield zip_buffer.getvalue()

# def get_recent_media_generator_from_keys(key: Union[str, List[str]]):
#     if isinstance(key, str):
#         key = [key]
#     zipped = get_recent_media_from_keys(key)
#     for zip_buffer in zipped:
#         yield zip_buffer.getvalue()




def pack_simulation_streamer_media_to_zip(sim: Simulation, key_event_map: Dict[str, List[Any]]):
    """ Packs media data from a single streamer into zipped bytes.

    Zips up media events from a streamer, creating a new file
    from each media event. The resulting zip contains all media
    files with relevant extensions and an index file containing
    information mapping the stat key and other data for each
    media file in the zip file.

    Args:
        sim: Simulation object to pack
        key_event_map: Maps stat keys to a list of events containing
            media information that must be zipped.
    Returns:
        Bytes buffer of the zipped information.
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        media_index = {}
        # For each stat key, iterate all the events
        # and write each event's associated media data to a
        # new file in the zip
        for key, media_events in key_event_map.items():
            file_prefix = f"{key}_"
            for i, event in enumerate(media_events):
                media_format = event_to_media_format(event)
                if media_format is None:
                    raise RuntimeError(f"No valid media format found for event '{event}' for key '{key}'")
                mime_type = media_format.mime if media_format.has_mimetype else ""
                ext = media_format.ext if media_format.has_extension else ""
                filename = file_prefix + str(i) + f".{ext}"
                if isinstance(event, ImageEvent):
                    zip_file.writestr(filename, event.encoded_image_string)
                    media_index[filename] = MediaMetadata(key=key, mimetype=mime_type, step=event.step, wall_time=event.wall_time)
                elif isinstance(event, AudioEvent):
                    zip_file.writestr(filename, event.encoded_audio_string)
                    media_index[filename] = MediaMetadata(key=key, mimetype=mime_type, step=event.step, wall_time=event.wall_time)
                elif isinstance(event, FileEvent):
                    zip_file.writestr(filename, event.encoded_string)
                    media_index[filename] = MediaMetadata(key=key, mimetype=mime_type, step=event.step, wall_time=event.wall_time)
        # Add the index file to the zip
        index_data = ZippedMediaFile(streamer_key="", sim_id=str(sim._project_sim_id), metadata=media_index)
        zip_file.writestr("index.json", json.dumps(index_data, cls=DataclassJSONEncoder))
    zip_buffer.seek(0)
    return zip_buffer

def get_recent_media_from_simulation(sim: Simulation, media_tags: List[str]=[], stat_keys: List[str]=[]) -> io.BytesIO:
    """
    Returns a zip file of all new media generated by the Simulation.
    """
    used_tags = set(media_tags)
    used_keys = set(stat_keys)
    all_media_keys = set()
    final_keys = set()
    # Generate a set of all stat keys that should be retrieved from
    # the simulation streamer.
    # We want all keys that are either:
    #   1) Part of any of the input media_tags
    #   2) Part of the input stat_keys AND whos associated tag is part of the MEDIA_TAG_SET

    # Gather all keys that are possible for all media tags
    tag_key_map = sim.streamer.get_tag_key_map()
    for media_tag in tags.MEDIA_TAG_SET:
        # Add all keys from that tag to the all_media_keys set
        if media_tag in tag_key_map:
            all_media_keys.update(tag_key_map[media_tag])
            # Add all keys from that tag to the available key set
            if media_tag in used_tags:
                final_keys.update(tag_key_map[media_tag])
    # Add all keys that were input and are media keys
    final_keys.update(all_media_keys.intersection(used_keys))
    
    # dictionary containing valid results from all streamers
    # with the key being each stat key and the values being
    # a list of the key's new events
    # Maps [stat key -> List[tb event value]]
    streamer_responses: Dict[str, List[Any]] = {}
    for key in final_keys:
        streamer = sim.streamer.get_streamer_for_key(key)
        streamer_responses[key] = streamer.get_recent_from_key(key)
        logger.info(f"Got {len(streamer_responses[key])} recent from key '{key}'")
    
    zip_buffer = pack_simulation_streamer_media_to_zip(sim, streamer_responses)
    with zipfile.ZipFile(zip_buffer, "r") as zip:
        print(f"zip file for sim '{sim._project_sim_id}': {zip.filelist}")
        print("index: ", zip.open("index.json").read())

    return zip_buffer

def get_recent_media_from_simulation_generator(sim: Simulation, media_tags: List[str]=[], stat_keys: List[str]=[]):
    zip_buffer = get_recent_media_from_simulation(sim, media_tags, stat_keys)
    yield zip_buffer.getvalue()










def pack_simulation_events_to_zip(sim: Simulation, key_event_map: Dict[str, List[Any]]):
    """ Packs media data from a single streamer into zipped bytes.

    Zips up events from a streamer, creating a new file
    from each media event and a new file for each scalar stat.
    Includes an index file with information on each internal file.

    Args:
        sim: Simulation object to pack
        key_event_map: Maps stat keys to a list of events containing
            information that must be zipped.
    Returns:
        Bytes buffer of the zipped information.
    """
    zip_buffer = io.BytesIO()
    streamer = sim.streamer
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        index = defaultdict(dict)
        # index = {
        #     "scalars": {},
        #     "images": {},
        #     "audio": {},
        # }
        # For each stat key, manage them appropriately
        for key, events in key_event_map.items():
            # Manage scalar key by stuffing into JSON file
            if streamer.key_has_tag(key, tags.TB_SCALARS):
                filename = f"{key}_scalars.json"
                zip_file.writestr(filename, json.dumps(
                    [{
                        "wall_time": event.wall_time,
                        "step": event.step,
                        "value": event.value
                    } for event in events]
                ))
                index["scalars"][filename] = JSONMetadata(key=key)
                logger.info(f"packing scalars for key '{key}' to file '{filename}'")
            # Manage media keys (images, audio)
            elif    streamer.key_has_tag(key, tags.TB_IMAGES) or \
                    streamer.key_has_tag(key, tags.TB_AUDIO) or \
                    streamer.key_has_tag(key, tags.VIDEOS):
                file_prefix = f"{key}_"
                for i, event in enumerate(events):
                    # Get true file format from event point data
                    media_format = event_to_media_format(event)
                    if media_format is None:
                        raise RuntimeError(f"No valid media format found for event '{event}' for key '{key}'")
                    mime_type = media_format.mime if media_format.has_mimetype else ""
                    ext = media_format.ext if media_format.has_extension else ""
                    filename = file_prefix + str(i) + f".{ext}"
                    if isinstance(event, ImageEvent):
                        zip_file.writestr(filename, event.encoded_image_string)
                        index["images"][filename] = MediaMetadata(key=key, mimetype=mime_type, step=event.step, wall_time=event.wall_time)
                        logger.info(f"packing image for key '{key}' at step '{event.step}' to file '{filename}'")
                    elif isinstance(event, AudioEvent):
                        zip_file.writestr(filename, event.encoded_audio_string)
                        index["audio"][filename] = MediaMetadata(key=key, mimetype=mime_type, step=event.step, wall_time=event.wall_time)
                        logger.info(f"packing audio for key '{key}' at step '{event.step}' to file '{filename}'")
                    elif isinstance(event, FileEvent):
                        zip_file.writestr(filename, event.encoded_string)
                        index[event.tag][filename] = MediaMetadata(key=key, mimetype=mime_type, step=event.step, wall_time=event.wall_time)
                        logger.info(f"packing file for key '{key}' at step '{event.step}' to file '{filename}'")
        # Add the index file to the zip
        index_data = ZippedIndex(streamer_key="", sim_id=str(sim._project_sim_id), metadata=dict(index))
        zip_file.writestr("index.json", json.dumps(index_data, cls=DataclassJSONEncoder))
        logger.info(f"packing index.json")
    zip_buffer.seek(0)
    return zip_buffer

def get_recent_from_simulation(
        sim: Simulation,
        media_tags: List[str]=[],
        stat_keys: List[str]=[],
        exclusion_mode: bool = False
    ) -> io.BytesIO:
    """
    Returns a zip file of newly generated data generated by the Simulation.

    Args:
        sim: Simulation from which we retrieve data.
        media_tags: List of stat types to retrieve. When exclusion_mode is False
            all keys from all tags in media_tags will be retrieved. When True,
            we exclude all keys from all tags in media_tags.
        stat_keys: List of keys to explicitly include. When exclusion_mode is
            True, stat_keys indicates specific keys that should be excluded
            from the final data.
        exclusion_mode: When false, media_tags and stat_keys act inclusively
            from an empty default. i.e. we only return those keys included by
            media_tags or stat_keys. When true, we include all keys by default
            and media_tags and stat_keys indicate which keys and tag types to
            exclude from the final result.
    """
    logger.info(f"get_recent_from_simulation: {sim._project_sim_id}, tags={media_tags}, keys={stat_keys}, exclusion_mode={exclusion_mode}")
    tag_key_map = sim.streamer.get_tag_key_map()
    tag_key_set = set()
    logger.debug(f"get_recent_from_simulation: {sim._project_sim_id}, tag_key_map={tag_key_map}, streamer.get_all_keys={sim.streamer.get_all_keys()}")
    for tag in media_tags:
        if tag in tag_key_map:
            tag_key_set.update([key for key_list in tag_key_map[tag] for key in key_list])
    specific_key_set = set(stat_keys)
    logger.debug(f"get_recent_from_simulation: {sim._project_sim_id}, curr tag_key_set={tag_key_set}, specific_key_set={specific_key_set}")
    # In exclusion_mode, we include all keys by default
    if exclusion_mode:
        final_keys = set([key for key, tag in sim.streamer.get_all_keys()])
        # Now exclude all keys from tags or specific
        final_keys.difference_update(tag_key_set.union(specific_key_set))
    else:
        # When not exclusionary, set the final keys to the
        # union of tag keys and specific keys
        final_keys = tag_key_set.union(specific_key_set)
    logger.info(f"get_recent_from_simulation final keys: {final_keys}")
    
    # dictionary containing valid results from all streamers
    # with the key being each stat key and the values being
    # a list of the key's new events
    # Maps [stat key -> List[tb event value]]
    streamer_responses: Dict[str, List[Any]] = {}
    for s in sim.streamer.streamers():
        s.Reload()
    for key in final_keys:
        streamer = sim.streamer.get_streamer_for_key(key)
        streamer_responses[key] = streamer.get_recent_from_key(key)
        logger.info(f"Got {len(streamer_responses[key])} recent from key '{key}'")
    
    zip_buffer = pack_simulation_events_to_zip(sim, streamer_responses)
    with zipfile.ZipFile(zip_buffer, "r") as zip:
        logger.debug(f"zip file for sim '{sim._project_sim_id}': {zip.filelist}")
        logger.debug("index: ", zip.open("index.json").read())

    zip_buffer.seek(0)
    return zip_buffer

def get_recent_from_simulation_generator(
    sim: Simulation,
    media_tags: List[str]=[],
    stat_keys: List[str]=[],
    exclusion_mode: bool = False
):
    logger.info(f"get_recent_from_simulation_generator: {sim._project_sim_id}, tags={media_tags}, keys={stat_keys}, exclusion_mode={exclusion_mode}")
    zip_buffer = get_recent_from_simulation(sim, media_tags, stat_keys, exclusion_mode)
    yield zip_buffer.getvalue()



def get_all_from_simulation(
        sim: Simulation,
        media_tags: List[str]=[],
        stat_keys: List[str]=[],
        exclusion_mode: bool = False
    ) -> io.BytesIO:
    """
    Returns a zip file of all data generated by the Simulation.

    Args:
        sim: Simulation from which we retrieve data.
        media_tags: List of stat types to retrieve. When exclusion_mode is False
            all keys from all tags in media_tags will be retrieved. When True,
            we exclude all keys from all tags in media_tags.
        stat_keys: List of keys to explicitly include. When exclusion_mode is
            True, stat_keys indicates specific keys that should be excluded
            from the final data.
        exclusion_mode: When false, media_tags and stat_keys act inclusively
            from an empty default. i.e. we only return those keys included by
            media_tags or stat_keys. When true, we include all keys by default
            and media_tags and stat_keys indicate which keys and tag types to
            exclude from the final result.
    """
    logger.info(f"get_all_from_simulation: {sim._project_sim_id}, tags={media_tags}, keys={stat_keys}, exclusion_mode={exclusion_mode}")
    tag_key_map = sim.streamer.get_tag_key_map()
    tag_key_set = set()
    for tag in media_tags:
        if tag in tag_key_map:
            tag_key_set.update([key for key_list in tag_key_map[tag] for key in key_list])
    specific_key_set = set(stat_keys)
    # In exclusion_mode, we include all keys by default
    if exclusion_mode:
        final_keys = set([key for key, tag in sim.streamer.get_all_keys()])
        # Now exclude all keys from tags or specific
        final_keys.difference_update(tag_key_set.union(specific_key_set))
    else:
        # When not exclusionary, set the final keys to the
        # union of tag keys and specific keys
        final_keys = tag_key_set.union(specific_key_set)
    logger.info(f"get_all_from_simulation final keys: {final_keys}")
    
    # dictionary containing valid results from all streamers
    # with the key being each stat key and the values being
    # a list of the key's new events
    # Maps [stat key -> List[tb event value]]
    streamer_responses: Dict[str, List[Any]] = {}
    for s in sim.streamer.streamers():
        s.reset_streamer()
        s.Reload()
    for key in final_keys:
        streamer = sim.streamer.get_streamer_for_key(key)
        logger.debug(f"got streamer for key '{key}': {streamer}")
        streamer_responses[key] = streamer.get_recent_from_key(key)
        logger.info(f"Got {len(streamer_responses[key])} recent from key '{key}'")
    
    zip_buffer = pack_simulation_events_to_zip(sim, streamer_responses)
    with zipfile.ZipFile(zip_buffer, "r") as zip:
        print(f"zip file for sim '{sim._project_sim_id}': {zip.filelist}")
        print("index: ", zip.open("index.json").read())

    zip_buffer.seek(0)
    return zip_buffer

def get_all_from_simulation_generator(
    sim: Simulation,
    media_tags: List[str]=[],
    stat_keys: List[str]=[],
    exclusion_mode: bool = False
):
    logger.info(f"get_all_from_simulation_generator: {sim._project_sim_id}, tags={media_tags}, keys={stat_keys}, exclusion_mode={exclusion_mode}")
    zip_buffer = get_all_from_simulation(sim, media_tags, stat_keys, exclusion_mode)
    yield zip_buffer.getvalue()