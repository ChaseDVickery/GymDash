import asyncio
import importlib.util
import logging
import os
import pickle
import sys
import traceback
from contextlib import asynccontextmanager
from random import randint
from threading import Thread

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import (FileResponse, JSONResponse, Response,
                               StreamingResponse)

import gymdash
from gymdash.backend.core.api.config.config import tags
from gymdash.backend.core.api.models import (SimulationInteractionModel,
                                             SimulationStartConfig,
                                             StoredSimulationInfo)
from gymdash.backend.core.api.stream import StreamerRegistry
from gymdash.backend.core.patch.patcher import apply_extension_patches
from gymdash.backend.core.simulation.examples import \
    register_example_simulations
from gymdash.backend.core.simulation.export import SimulationExporter
from gymdash.backend.core.simulation.manage import (SimulationRegistry,
                                                    SimulationTracker)
from gymdash.backend.core.utils.usage import *
from gymdash.backend.core.utils.zip import get_recent_media_generator_from_keys
from gymdash.backend.project import ProjectManager

logger = logging.getLogger(__name__)
logging.basicConfig(level = logging.INFO, format = '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s')

simulation_tracker = SimulationTracker()
apply_extension_patches()

register_example_simulations()
SimulationExporter.import_and_register()
ProjectManager.import_args_from_file()

# App main
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Executed right before we handle requests
    # asyncio.create_task(manage_simulation_loop())
    yield
    # Executed right before app shutdown
    pass

# Setup our API
app = FastAPI(
    title="GymDash",
    description="API for interacting with active simulation environments",
    version="0.0.1",
    lifespan=lifespan
)

# Setup CORS middleware so that our API will accept
# communication from our frontend
origins = [
    "*"
]
regex_origins = None
# regex_origins = r"^((.*127.0.0.1.*)|(.*localhost.*))$"
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
    # minimum_size=1_000_000,  # 1MB
    minimum_size=16 * (2**10), # 16KiB
    # Compression level 1-9 (1 lowest compression, 9 highest compression)
    compresslevel=1
)


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
    return StreamingResponse(
        content=get_recent_media_generator_from_keys(
            ["episode_video", "episode_video_thumbnail"]
        ),
        media_type="application/zip"
    )
    
@app.post("/start-new-test")
async def start_new_simulation_call(config: SimulationStartConfig):
    logger.debug(f"API called start-new-test with config: {config}")
    id, _ = simulation_tracker.start_sim(config)
    return { "id": str(id) }

@app.post("/query-sim")
async def get_sim_progress(sim_query: SimulationInteractionModel):
    query_response = await simulation_tracker.fulfill_query_interaction(sim_query)
    return query_response

@app.get("/get_sims_history")
async def get_stored_simulations():
    sim_infos = ProjectManager.get_filtered_simulations()
    return sim_infos

    
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