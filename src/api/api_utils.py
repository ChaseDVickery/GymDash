from tensorboard.backend.event_processing.event_accumulator import ImageEvent, AudioEvent
from src.api.internals.logging.streamables.StreamerRegistry import StreamerRegistry
import src.api.internals.stat_tags as tags
from fastapi.responses import Response, JSONResponse, StreamingResponse
from typing import Dict, List, Union, Any
# import magic
# import base64
import json
import io
import zipfile
from dataclasses import dataclass, is_dataclass, asdict

@dataclass(frozen=True)
class MediaMetadata:
    """Contains information for an arbitrary media file represented as bytes.

    Attributes:
      mimetype: MIME type of file.
    """
    mimetype: str

@dataclass(frozen=True)
class ZippedMediaFile:
    streamer_key: str
    metadata: Dict[str, MediaMetadata]


# https://stackoverflow.com/questions/51286748/make-the-python-json-encoder-support-pythons-new-dataclasses
class DataclassJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if is_dataclass(o):
            return asdict(o)
        return super().default(o)


# def tb_media_to_json(event: List[Union[ImageEvent, AudioEvent]]):
#     """Encode the event data as a JSON string and then encode that as a b64 string."""
#     return base64.b64encode(json.dumps(event))

def tb_event_to_media_type(event):
    """
    Return the mimetype for the contents of a media file
    logged in a tensorboard file. Returns None if no
    such event or if conversion cannot find suitable
    indicators of a particular type.
    """
    # https://stackoverflow.com/questions/57785500/how-to-know-mime-type-of-a-file-from-base64-encoded-data-in-python
    media_string = None
    if isinstance(event, ImageEvent):
        media_string = event.encoded_image_string
        return "image/gif"
    elif isinstance(event, AudioEvent):
        media_string = event.encoded_audio_string
        return "audio/wav"
    
    if not media_string:
        return None
    
    # guess = magic.from_buffer(base64.b64decode(media_string), mime=True)
    # return guess
    return 
    

def pack_streamer_media_to_zip(streamer_key, key_event_map):
    """
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        media_index = {}
        for key, media_events in key_event_map.items():
            file_prefix = f"{key}_"
            for i, event in enumerate(media_events):
                media_type = tb_event_to_media_type(event)
                media_type = media_type if media_type else ""
                filename = file_prefix + str(i) + ".bytes"
                if isinstance(event, ImageEvent):
                    zip_file.writestr(filename, event.encoded_image_string)
                    media_index[filename] = MediaMetadata(mimetype=media_type)
                elif isinstance(event, AudioEvent):
                    zip_file.writestr(filename, event.encoded_audio_string)
                    media_index[filename] = MediaMetadata(mimetype=media_type)
        # Add the index file to the zip
        index_data = ZippedMediaFile(streamer_key, media_index)
        zip_file.writestr("index.json", json.dumps(index_data, cls=DataclassJSONEncoder))
    zip_buffer.seek(0)
    return zip_buffer

def get_recent_media(media_tag: str, key: str):
    if media_tag not in tags.MEDIA_TAG_SET:
        print(f"get_recent_media tried to retrieve media from tag '{media_tag}' but it is not a media tag")
        return {}
    
    # dictionary containing valid results from all streamers
    # with the key being each streamer's streamer_name/from
    # the StreamerRegistry key
    # Maps [streamer key -> [stat key -> List[tb event value]]]
    streamer_responses: Dict[str, Dict[str, List[Any]]] = {}
    for streamer_key, streamer in StreamerRegistry.items():
        recent = streamer.get_recent_from_tag(media_tag)
        if key not in recent:
            continue
        event_values = recent[key]
        if len(event_values) < 1:
            continue

        # streamer_responses[streamer_key] = event_values
        streamer_responses[streamer_key] = {
            key: event_values
        }
        print(f"api recent test things count: {len(event_values)}")
    
    # print(f"streamer responses: {streamer_responses}")
    zipped = []
    for streamer_key, key_media_responses in streamer_responses.items():
        zip_buffer = pack_streamer_media_to_zip(streamer_key, key_media_responses)
        zipped.append(zip_buffer)
        with zipfile.ZipFile(zip_buffer, "r") as zip:
            print(f"zip file for streamer '{streamer_key}': {zip.filelist}")
            print("index: ", zip.open("index.json").read())

    return zipped

def get_recent_media_generator(media_tag: str, key: str):
    zipped = get_recent_media(media_tag, key)
    for zip_buffer in zipped:
        yield zip_buffer.getvalue()
        # with zipfile.ZipFile(zip_buffer, "r") as zip_read:
        #     print(zip_read)
        #     print(type(zip_read))
        #     yield zip_read.read()