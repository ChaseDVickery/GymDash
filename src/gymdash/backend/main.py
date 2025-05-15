import asyncio
import logging
from contextlib import asynccontextmanager
from random import randint
from threading import Thread
from typing import Union
from gymdash.backend.core.utils.thread_utils import execute_queued

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import (FileResponse, JSONResponse, Response,
                               StreamingResponse)

import gymdash
from gymdash.backend.core.api.config.config import tags
from gymdash.backend.core.api.models import (SimulationIDModel,
                                             SimulationIDsModel,
                                             SimulationInteractionModel,
                                             SimulationStartConfig,
                                             StoredSimulationInfo, StatQuery)
from gymdash.backend.core.patch.patcher import apply_extension_patches
from gymdash.backend.core.simulation.examples import \
    register_example_simulations
from gymdash.backend.core.simulation.export import SimulationExporter
from gymdash.backend.core.simulation.manage import (SimulationRegistry,
                                                    SimulationTracker)
from gymdash.backend.core.utils.usage import *
# from gymdash.backend.core.utils.zip import get_recent_media_generator_from_keys
from gymdash.backend.core.utils.zip import \
    get_recent_media_from_simulation_generator, get_recent_from_simulation_generator, get_all_from_simulation_generator
from gymdash.backend.project import ProjectManager

logger = logging.getLogger(__name__)
# logging.basicConfig(level = logging.DEBUG, format = '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s')
logging.basicConfig(level = logging.INFO, format = '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s')

simulation_tracker = SimulationTracker()
# Apply patching methods to other packages
apply_extension_patches()
# Register default simulations
register_example_simulations()
# Register custom simulations
SimulationExporter.import_and_register()
# Set up project structure and database
ProjectManager.import_args_from_file()
# Load old streamers from disk
# ProjectManager.get_filtered_simulations_where("is_done=? OR force_stopped=?", (int(True), int(True)))
finished_sim_info = ProjectManager.get_filtered_simulations(
    is_done=int(True),
    force_stopped=int(True),
    set_mode="OR"
)
simulation_tracker.load_old_simulations_from_info(finished_sim_info)

async def side_loop():
    while True:
        execute_queued()
        await asyncio.sleep(2)

# App main
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Executed right before we handle requests
    asyncio.create_task(side_loop())
    yield
    # Executed right before app shutdown
    # Clearing the simulation tracker also
    # tells all running simulations to shutdown
    try:
        logger.info(f"Shutting down API server.")
        simulation_tracker.stop()
        await simulation_tracker.clear()
    except KeyboardInterrupt:
        logger.warning(f"Force shutdown may cause unfinishable simulations.")
    finally:
        for id, sim in simulation_tracker.running_sim_map.items():
            sim.force_stopped = True
            sim._meta_cancelled = True
            ProjectManager._add_or_update_simulation(id, sim)

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
    raise HTTPException(status_code=404, detail="all-recent-images endpoint is not implemented")
    sim = list(simulation_tracker.done_sim_map.values())[0]
    return StreamingResponse(
        content=get_recent_media_from_simulation_generator(
            sim,
            media_tags=[],
            stat_keys=["episode_video", "episode_video_thumbnail"]
        ),
        media_type="application/zip"
    )

@app.post("/sim-recent-media")
async def get_sim_recent_media(sim_id: SimulationIDModel):
    sim = simulation_tracker.get_sim(sim_id.id)
    if sim is None:
        raise HTTPException(
            status_code=404,
            detail=f"sim-recent-media endpoint found no simulation with id '{sim_id.id}'"
        )
    return StreamingResponse(
        content=get_recent_media_from_simulation_generator(
            sim,
            media_tags=[],
            stat_keys=["episode_video"]
        ),
        media_type="application/zip"
    )
    
@app.post("/start-new-test")
async def start_new_simulation_call(config: SimulationStartConfig):
    logger.debug(f"API called start-new-test with config: {config}")
    if simulation_tracker.is_clearing:
        return { "id": str(simulation_tracker.no_id) }
    id, _ = simulation_tracker.start_sim(config)
    return { "id": str(id) }
@app.post("/queue-new-sim")
async def queue_new_simulation_call(config: SimulationStartConfig):
    logger.debug(f"API called queue-new-sim with config: {config}")
    if simulation_tracker.is_clearing:
        return { "id": str(simulation_tracker.no_id) }
    id, _ = simulation_tracker.queue_sim(config)
    return { "id": str(id) }

@app.post("/cancel-sim")
async def cancel_sim(sim_query: Union[SimulationInteractionModel, SimulationIDModel]):
    if simulation_tracker.is_clearing:
        return {}
    query_response = await simulation_tracker.stop_simulation_call(sim_query.id)
    return query_response
@app.post("/query-sim")
async def get_sim_progress(sim_query: SimulationInteractionModel):
    if simulation_tracker.is_clearing:
        return {}
    query_response = await simulation_tracker.fulfill_query_interaction(sim_query)
    return query_response

@app.get("/get-sims-history")
async def get_stored_simulations():
    sim_infos = ProjectManager.get_filtered_simulations()
    return sim_infos

@app.get("/delete-all-sims")
async def get_delete_all_simulations():
    if simulation_tracker.is_clearing:
        return {}
    # Stop all current simulations and clear tracker
    responses = await simulation_tracker.clear()
    # Clear backend DB of simulations
    ProjectManager.delete_all_simulations_immediate()
    return responses

@app.post("/delete-sims")
async def get_delete_simulations(sim_ids: SimulationIDsModel):
    if simulation_tracker.is_clearing:
        return {}
    # Stop specific current simulations
    responses = await simulation_tracker.clear_specific(sim_ids.ids)
    # Remove from backend DB of simulations
    ProjectManager.delete_specific_simulations_immediate(sim_ids.ids)
    # ProjectManager.delete_all_simulations_immediate()
    return responses

@app.post("/get-sim-status")
async def get_simulation_status(sim_ids: SimulationIDsModel):
    if simulation_tracker.is_clearing:
        return []
    return ProjectManager.get_latest_statuses(sim_ids.ids)

    
@app.get("/all-recent-scalars")
async def get_all_recent_scalars():
    raise HTTPException(status_code=404, detail="all-recent-scalars endpoint is not implemented")
    # for streamer in StreamerRegistry.streamers():
    #     recent = streamer.get_recent_from_tag(tags.TB_SCALARS)
    #     return recent

@app.post("/sim-data-recent")
async def get_sim_data_recent(query: StatQuery):
    sim = simulation_tracker.get_sim(query.id)
    if sim is None:
        raise HTTPException(
            status_code=404,
            detail=f"sim-data-recent endpoint found no simulation with id '{query.id}'"
        )
    return StreamingResponse(
        content=get_recent_from_simulation_generator(
            sim,
            media_tags=query.tags,
            stat_keys=query.keys,
            exclusion_mode=query.exclusion_mode
        ),
        media_type="application/zip"
    )

@app.post("/sim-data-all")
async def get_sim_data_all(query: StatQuery):
    sim = simulation_tracker.get_sim(query.id)
    if sim is None:
        raise HTTPException(
            status_code=404,
            detail=f"sim-data-all endpoint found no simulation with id '{query.id}'"
        )
    return StreamingResponse(
        content=get_all_from_simulation_generator(
            sim,
            media_tags=query.tags,
            stat_keys=query.keys,
            exclusion_mode=query.exclusion_mode
        ),
        media_type="application/zip"
    )
    
@app.get("/get-control-requests")
async def get_control_requests():
    return StreamingResponse(simulation_tracker.control_request_generator(), media_type="text/event-stream")