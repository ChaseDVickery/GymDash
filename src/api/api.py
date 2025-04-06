from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response, FileResponse, StreamingResponse
from random import randint
import numpy as np

import traceback

from threading import Thread
from src.tests.stock.train import train, train_cartpole

from src.api.internals.logging.streamables.StreamerRegistry import StreamerRegistry
import src.api.internals.stat_tags as tags

from src.api.api_models import SimulationStartConfig
from src.api.internals.extensions.patch import apply_extension_patches
import src.api.api_utils as api_utils

from .internals.usage import get_usage_simple, get_usage_detailed, get_usage_gpu





apply_extension_patches()

# Setup our API
app = FastAPI(title="GymDash", description="API for interacting with active simulation environments", version="0.0.1")

# Setup CORS middleware so that our API will accept
# communication from our frontend
origins = [
    # "*"
]
regex_origins = r"^((.*127.0.0.1.*)|(.*localhost.*))$"
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=regex_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup gzip compression middleware
# https://fastapi.tiangolo.com/advanced/middleware/#trustedhostmiddleware
app.add_middleware(
    GZipMiddleware,
    # Messages below minimum_size (in bytes) will not be compressed
    minimum_size=1_000_000,
    # Compression level 1-9 (1 lowest compression, 9 highest compression)
    compresslevel=1
)

def run_test_simulation(config: SimulationStartConfig):
    if not SimulationStartConfig:
        raise ValueError("No SimulationStartConfig provided")
    else:
        if (config.name == "cartpole"):
            train_cartpole(**config.kwargs)
        elif (config.name == "stock"):
            train()
        else:
            raise ValueError(f"SimulationStartConfig name '{config.name}' is not recognized. Try one of (cartpole, stock)")
    

def start_test_simulation(config: SimulationStartConfig):
    sim_listener_thread = Thread(target=run_test_simulation, args=(config,))
    sim_listener_thread.start()

@app.get("/")
async def test():
    return {
        "Message": "This is the result of an API call."
    }

@app.get("/random")
async def thinking_of_a_number():
    return {
        "value": randint(1, 10)
    }

@app.get("/big-data1000")
async def thinking_of_a_number2():
    return {
        "value": np.random.random((10, 10, 10)).flatten().tolist()
    }

@app.get("/big-data100000")
async def thinking_of_a_number3():
    return {
        "value": np.random.random(100_000).flatten().tolist()
    }

# https://stackoverflow.com/questions/73921756/how-to-add-gzip-middleware-for-the-fastapi
@app.get("/big-data1000000")
async def thinking_of_a_number4():
    return {
        "value": np.random.random((100, 100, 100)).flatten().tolist()
    }

@app.get("/resource-usage-simple")
async def get_resource_usage_simple():
    return get_usage_simple()

@app.get("/resource-usage-detailed")
async def get_resource_usage_detailed():
    return get_usage_detailed()

@app.get("/resource-usage-gpu")
async def get_resource_usage_gpu():
    return get_usage_gpu()

@app.get("/all-recent-images")
async def get_all_recent_images():
    # print(get_recent_media(tags.TB_IMAGES, "episode_video"))
    return StreamingResponse(content=api_utils.get_recent_media_generator(tags.TB_IMAGES, "episode_video"), media_type="application/zip")

    # for streamer in StreamerRegistry.streamers():
    #     # print(streamer)
    #     recent = streamer.get_recent_from_tag(tags.TB_IMAGES)
    #     all = streamer.get_all_from_tag(tags.TB_IMAGES)
    #     print(f"api total test things count: {len(recent['episode_video'])}")
    #     print(f"api new test things count: {len(recent['episode_video'])}")
    #     if (len(recent["episode_video"]) > 0):
    #         for i in range(len(recent["episode_video"])):
    #             d = recent['episode_video'][i]
    #             print(f"api image values: wall_time={d.wall_time}, step={d.step}, width={d.width}, height={d.height}, encoded_len={len(d.encoded_image_string)}")
    #     # return {}
    #     if (len(recent['episode_video']) < 1):
    #         return {}
    #     response = Response(content=recent["episode_video"][0].encoded_image_string, media_type="image/gif")
    #     # response = Response(content=recent["episode_video"][0].encoded_image_string, media_type="application/octet-stream")
    #     return response
    #     # return recent
    
@app.post("/start-new-test")
async def start_new_simulation_call(config: SimulationStartConfig):
    start_test_simulation(config)
    
@app.get("/all-recent-scalars")
async def get_all_recent_scalars():
    for streamer in StreamerRegistry.streamers():
        recent = streamer.get_recent_from_tag(tags.TB_SCALARS)
        return recent

@app.get("/read-key/")
async def get_read_test(exp_key: str, key: str, recent: bool = True):
    """
    Parameters:
        exp_key:    The experiment key. Points towards the
            internal tb file containing the stats.
        key:        The scalar stat key to query.
        recent:     If true, only queries and returns the
            most recently acquired values from the key.
            If false, returns the entire data sequence.
    """
    streamer = StreamerRegistry.get_streamer(exp_key)
    print(f"Got streamer: '{streamer}'")
    if not streamer:
        print(f"No streamer '{exp_key}'")
        return {}
    else:
        try:
            recent = streamer.get_all_recent()
            print(recent)
            return recent
        except Exception as e:
            print(f"caught exception: {e}")
            traceback.print_exc()
        return {}