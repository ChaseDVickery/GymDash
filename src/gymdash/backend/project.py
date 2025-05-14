import argparse
import asyncio
import functools
import json
import logging
import os
import pickle
import sqlite3
import uuid
import shutil
from datetime import date, datetime
from pathlib import Path
from threading import Lock
from typing import Any, List, Tuple, Dict, Union, Literal, Iterable

from typing_extensions import Self

from gymdash.backend.core.api.models import (SimulationStartConfig,
                                             StoredSimulationInfo,
                                             SimStatus)
from gymdash.backend.core.simulation.base import Simulation
from gymdash.backend.enums import SimStatusCode

logger = logging.getLogger(__name__)

class KwargWrapper:
    def __init__(self, kwargs):
        self._kwargs = kwargs if kwargs is not None else {}

def uuid2text(id: uuid.UUID):
    return str(id)
def config2text(config: SimulationStartConfig):
    return json.dumps(config, cls=SimulationStartConfig.Encoder)
def kwargs2text(kwargs: KwargWrapper):
    return json.dumps(kwargs._kwargs)
sqlite3.register_adapter(uuid.UUID, uuid2text)
sqlite3.register_adapter(SimulationStartConfig, config2text)
sqlite3.register_adapter(KwargWrapper, kwargs2text)
sqlite3.register_adapter(bool, int)
# Converter objects are always passed a bytes object, so handle that
def text2uuid(byte_text):
    text = byte_text.decode("utf-8")
    return uuid.UUID(text)
def text2config(byte_text):
    text = byte_text.decode("utf-8")
    return json.loads(text, object_hook=SimulationStartConfig.custom_decoder)
def text2kwargs(byte_text):
    text = byte_text.decode("utf-8")
    return json.loads(text)
sqlite3.register_converter("UUID", text2uuid)
sqlite3.register_converter("SIMULATIONCONFIG", text2config)
sqlite3.register_converter("KWARGS", text2kwargs)
sqlite3.register_converter("BOOL", lambda i: bool(int(i)))

class ProjectManager:
    def immediate(func):
        def wrapper(*args, **kwargs):
            # Run cached executions early so we don't
            # immediately repopulate with old stuff
            ProjectManager.run_cached_executions()
            ProjectManager._execution_mutex.acquire()
            result = func(*args, **kwargs)
            ProjectManager._execution_mutex.release()
            return result
        return wrapper

    ARGS_FILENAME   = "args.pickle"
    TB_FOLDER       = "tb"
    SIMS_FOLDER     = "sims"
    DB_FOLDER       = "db"
    RES_FOLDER      = "resources"
    DB_NAME         = "simulations.db"

    _execution_mutex = Lock()
    _cached_executions: List[Tuple[str, Any]] = []

    @staticmethod
    def get_con() -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
        return ProjectManager.dbcon, ProjectManager.dbcur

    @staticmethod
    def setup_from_args(args):
        ProjectManager.args = args
        ProjectManager.dbcon: sqlite3.Connection = None
        ProjectManager.dbcur: sqlite3.Cursor = None
        ProjectManager._setup_project_structure()
        ProjectManager._setup_database()
        ProjectManager._setup_loop()

    @staticmethod
    def _get_export_folder() -> Path:
        path = Path(os.path.dirname(__file__), "exported_args")
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Could not create project args export folder")
        return path

    @staticmethod
    def import_args_from_file():
        export_folder = ProjectManager._get_export_folder()
        args_filepath = os.path.join(export_folder, ProjectManager.ARGS_FILENAME)
        # Try to read in exported files
        if not os.path.exists(args_filepath):
            logger.error(f"ProjectManager cannot import_args_from_file because args file at '{args_filepath}' does not exist.")
            return False
        try:
            with open(args_filepath, "rb") as f:
                args = argparse.Namespace(**dict(pickle.load(f)))
                ProjectManager.setup_from_args(args)
        except Exception as e:
            logger.exception(f"Exception while reading args file from '{args_filepath}'")
            return False
        logger.info(f"ProjectManager successfully imported args.")
        return True
    
    @staticmethod
    def export_args(args: argparse.Namespace):
        export_folder = ProjectManager._get_export_folder()
        args_filepath = os.path.join(export_folder, ProjectManager.ARGS_FILENAME)
        # Try to export index
        try:
            with open(args_filepath, "wb") as f:
                pickle.dump(args._get_kwargs(), f)
        except Exception as e:
            logger.exception(f"Exception while exporting ProjectManager args file to '{args_filepath}'")
            return False
        logger.info(f"Successfully exported ProjectManager args.")
        return True


    @staticmethod
    def project_folder():
        return ProjectManager.args.project_dir
    @staticmethod
    def tb_folder():
        return os.path.join(ProjectManager.project_folder(), ProjectManager.TB_FOLDER)
    @staticmethod
    def sims_folder():
        return os.path.join(ProjectManager.project_folder(), ProjectManager.SIMS_FOLDER)
    @staticmethod
    def db_folder():
        return os.path.join(ProjectManager.project_folder(), ProjectManager.DB_FOLDER)
    @staticmethod
    def resources_folder():
        return os.path.join(ProjectManager.project_folder(), ProjectManager.RES_FOLDER)
    @staticmethod
    def db_path():
        return os.path.join(ProjectManager.db_folder(), ProjectManager.DB_NAME)

    @staticmethod
    def _setup_project_structure():
        try:
            # Base directory
            path = Path(ProjectManager.project_folder())
            path.mkdir(parents=True, exist_ok=True)
            # Sub-dirs
            os.makedirs(ProjectManager.tb_folder(),     exist_ok=True)
            os.makedirs(ProjectManager.db_folder(),     exist_ok=True)
            os.makedirs(ProjectManager.sims_folder(),   exist_ok=True)
        except Exception as e:
            logger.error(f"Problem setting up project structure at base directory '{ProjectManager.args.project_dir}'")
            raise e
        
    @staticmethod
    def _setup_database():
        ProjectManager.dbcon = sqlite3.connect(ProjectManager.db_path(), detect_types=sqlite3.PARSE_DECLTYPES)
        ProjectManager.dbcon.execute("PRAGMA foreign_keys = ON;")
        ProjectManager.dbcur = ProjectManager.dbcon.cursor()
        ProjectManager._create_simulations_table()
        ProjectManager._create_status_table()
        ProjectManager._create_api_call_table()

    @staticmethod
    def _create_simulations_table():
        con, cur = ProjectManager.get_con()
        cur = ProjectManager.dbcur
        cur.execute("""CREATE TABLE IF NOT EXISTS simulations (
                        sim_id UUID PRIMARY KEY,
                        name TEXT,
                        created TIMESTAMP,
                        started TIMESTAMP,
                        ended TIMESTAMP,
                        is_done BOOL,
                        cancelled BOOL,
                        failed BOOL,
                        force_stopped BOOL,
                        config SIMULATIONCONFIG,
                        start_kwargs KWARGS,
                        sim_type_name TEXT,
                        sim_module_name TEXT
                        )""")
        con.commit()
    @staticmethod
    def _create_status_table():
        con, cur = ProjectManager.get_con()
        cur = ProjectManager.dbcur
        cur.execute("""CREATE TABLE IF NOT EXISTS sim_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sim_id INTEGER NOT NULL,
                    time TIMESTAMP,
                    code INTEGER,
                    subcode INTEGER,
                    details TEXT,
                    error_trace TEXT,
                    FOREIGN KEY (sim_id)
                        REFERENCES simulations (sim_id)
                    )""")
        con.commit()
    @staticmethod
    def _create_api_call_table():
        con, cur = ProjectManager.get_con()
        cur = ProjectManager.dbcur
        cur.execute("""CREATE TABLE IF NOT EXISTS api_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    time TIMESTAMP,
                    code INTEGER,
                    details TEXT
                    )""")
        con.commit()

    @staticmethod
    def _setup_loop():
        # loop = asyncio.get_event_loop()
        asyncio.create_task(ProjectManager.run_cached_executions_loop())

    @staticmethod
    async def run_cached_executions_loop():
        while True:
            await asyncio.sleep(1)
            ProjectManager.run_cached_executions()
            
    @staticmethod
    def run_cached_executions():
        con, cur = ProjectManager.get_con()
        try:
            ProjectManager._execution_mutex.acquire()
            if len(ProjectManager._cached_executions) > 0:
                logger.info(f"ProjectManager running {len(ProjectManager._cached_executions)} cached executions")
            for exec_info in ProjectManager._cached_executions:
                exec_info()
            ProjectManager._cached_executions.clear()
            ProjectManager._execution_mutex.release()
        except Exception as e:
            logger.error(f"Error running cached executions: {ProjectManager._cached_executions}")
            ProjectManager._execution_mutex.release()
            raise e
        con.commit()


    @staticmethod
    def _add_or_update_simulation(sim_id: uuid.UUID, sim: Simulation):
        if sim is None: return
        con, cur = ProjectManager.get_con()

        check_text = "SELECT COUNT(sim_id) FROM simulations WHERE sim_id=?"
        existing = cur.execute(check_text, (sim_id,)).fetchone()
        
        if (existing[0] < 1):
            sim_update_text = """
            INSERT INTO simulations
            (
                sim_id,
                name,
                created,
                started,
                ended,
                is_done,
                cancelled,
                failed,
                force_stopped,
                config,
                start_kwargs,
                sim_type_name,
                sim_module_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                sim_id,
                sim.name,
                sim._meta_create_time,
                sim._meta_start_time,
                sim._meta_end_time,
                sim.is_done,
                sim._meta_cancelled,
                sim._meta_failed,
                sim.force_stopped,
                sim.config,
                KwargWrapper(sim.start_kwargs),
                type(sim).__name__,
                type(sim).__module__
            )
        else:
            sim_update_text = """
            UPDATE simulations
            SET
                name=?,
                created=?,
                started=?,
                ended=?,
                is_done=?,
                cancelled=?,
                failed=?,
                force_stopped=?,
                config=?,
                start_kwargs=?,
                sim_type_name=?,
                sim_module_name=?
            WHERE sim_id=?
            """
            params = (
                sim.name,
                sim._meta_create_time,
                sim._meta_start_time,
                sim._meta_end_time,
                sim.is_done,
                sim._meta_cancelled,
                sim._meta_failed,
                sim.force_stopped,
                sim.config,
                KwargWrapper(sim.start_kwargs),
                type(sim).__name__,
                type(sim).__module__,
                sim_id
            )
        cur.execute(sim_update_text, params)
        # Also add any statuses that it contains to the status table
        ProjectManager._add_simulation_statuses(sim_id, sim)

    @staticmethod
    def add_or_update_simulation(sim_id: uuid.UUID, sim: Simulation):
        ProjectManager._cached_executions.append(
            functools.partial(ProjectManager._add_or_update_simulation, sim_id=sim_id, sim=sim)
        )
    @staticmethod
    @immediate
    def add_or_update_simulation_immediate(sim_id: uuid.UUID, sim: Simulation):
        ProjectManager._add_or_update_simulation(sim_id, sim)

    @staticmethod
    def add_simulation_statuses(sim_id: uuid.UUID, sim: Simulation):
        ProjectManager._cached_executions.append(
            functools.partial(ProjectManager._add_simulation_statuses, sim_id=sim_id, sim=sim)
        )
    @staticmethod
    def _add_simulation_statuses(sim_id: uuid.UUID, sim: Simulation):
        if sim is None: return
        con, cur = ProjectManager.get_con()
        params = []
        update_text = """
            INSERT INTO sim_status
            (
                sim_id,
                time,
                code,
                subcode,
                details,
                error_trace
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """
        for status in sim.retrieve_new_statuses():
            params.append((
                sim_id,
                status.time,
                int(status.code),
                status.subcode,
                status.details,
                status.error_trace
            ))
        cur.executemany(update_text, params)

    @staticmethod
    def retrieval_to_sim_status(info) -> SimStatus:
        return SimStatus(
            time            = info[1],
            code            = info[2],
            subcode         = info[3],
            details         = info[4],
            error_trace     = info[5]
        )
    #     class SimStatus(BaseModel):
    # code:       SimStatusCode
    # time:       Union[datetime,None] = None
    # subcode:    int             = 0 # subcode is a subspecifier for what happened. 0 is nothing.
    # details:    str             = ""
    # error_trace:str             = ""

    @staticmethod
    def retrieval_to_stored_info(info) -> StoredSimulationInfo:
        return StoredSimulationInfo(
            sim_id      = info[0],
            name        = info[1],
            created     = info[2],
            started     = info[3],
            ended       = info[4],
            is_done     = info[5],
            cancelled   = info[6],
            failed      = info[7],
            force_stopped = info[8],
            config      = info[9],
            start_kwargs = info[10],    # should be a KwargWrapper after conversion. Fetch just the dict
            sim_type_name = info[11],
            sim_module_name = info[12],
        )

    @staticmethod
    def get_filtered_simulations_where(where_query: str, exec_args):
        con, cur = ProjectManager.get_con()

        query_text = f"""
        SELECT
            sim_id, name, created, started, ended, is_done, cancelled, failed, force_stopped, config, start_kwargs, sim_type_name, sim_module_name
        FROM
            simulations
        WHERE
            {where_query}
        ORDER BY
            created ASC
        """
        cur.execute(query_text, exec_args)

        res = cur.fetchall()
        results = []
        for info in res:
            results.append(
                ProjectManager.retrieval_to_stored_info(info)
            )
        logger.debug(f"Got {len(results)} db results")
        return results
    
    @staticmethod
    def get_latest_statuses(sim_ids: Iterable[Union[str, uuid.UUID]]):
        statuses = ProjectManager.get_all_latest_statuses()
        filtered_statuses = {}
        for simID in sim_ids:
            if str(simID) in statuses:
                filtered_statuses[str(simID)] = statuses[str(simID)]
            else:
                filtered_statuses[str(simID)] = None
        return filtered_statuses
    
    def get_all_latest_statuses() -> Dict[str, SimStatus]:
        con, cur = ProjectManager.get_con()
        query_text = f"""
        SELECT
            sim_id,
            MAX(time),
            code,
            subcode,
            details,
            error_trace
        FROM
            sim_status
        GROUP BY
            sim_id
        """
        cur.execute(query_text)
        res = cur.fetchall()
        results = {}
        for info in res:
            simID = str(info[0])
            results[simID] = ProjectManager.retrieval_to_sim_status(info)
        logger.debug(f"Got {len(results)} db results")
        return results

    @staticmethod
    def get_filtered_simulations(
        sim_id:Union[str,uuid.UUID]=None,
        # started:datetime=None,
        # ended:datetime=None,
        is_done:bool=None,
        cancelled:bool=None,
        failed:bool=None,
        force_stopped:bool=None,
        set_mode:Literal["OR", "AND"]="OR"
    ) -> List[StoredSimulationInfo]:
        con, cur = ProjectManager.get_con()

        exec_args = []
        filters = []
        if sim_id is not None:
            filters.append("sim_id=?")
            exec_args.append(sim_id)
        # if started is not None:
        #     filters.append("started=?")
        # if ended is not None:
        #     filters.append("ended=?")
        if is_done is not None:
            filters.append("is_done=?")
            exec_args.append(int(is_done))
        if cancelled is not None:
            filters.append("cancelled=?")
            exec_args.append(int(cancelled))
        if failed is not None:
            filters.append("failed=?")
            exec_args.append(int(failed))
        if force_stopped is not None:
            filters.append("force_stopped=?")
            exec_args.append(int(force_stopped))
        
        has_filter = len(filters) > 0

        filter_string = (" " + set_mode + " ").join(filters)
        query_text = f"""
        SELECT
            sim_id, name, created, started, ended, is_done, cancelled, failed, force_stopped, config, start_kwargs, sim_type_name, sim_module_name
        FROM
            simulations
        {'WHERE' if has_filter else ''}
            {filter_string}
        ORDER BY
            created ASC;
        """
        cur.execute(query_text, exec_args)

        res = cur.fetchall()
        results = []
        for info in res:
            results.append(
                ProjectManager.retrieval_to_stored_info(info)
            )
        logger.error(f"Got {len(results)} db results")
        return results
    
    @staticmethod
    @immediate
    def delete_all_simulations_immediate():
        ProjectManager._delete_all_simulations()
    @staticmethod
    def _delete_all_simulations():
        # Clear simulation table
        con, cur = ProjectManager.get_con()
        # Must drop sim_status first because it has FKs
        # that refer to simulation table entries.
        cur.execute("DROP TABLE sim_status")
        cur.execute("DROP TABLE simulations")
        ProjectManager._create_simulations_table()
        ProjectManager._create_status_table()
        con.commit()
        logger.info("Cleared table 'simulations'")
        logger.info("Cleared table 'sim_status'")
        # Delete all simulation subfolders if possible
        shutil.rmtree(ProjectManager.sims_folder(), ignore_errors=True)
        ProjectManager._setup_project_structure()
        logger.info(f"Cleared simulation subfolder at '{ProjectManager.sims_folder()}'")
    @staticmethod
    def delete_all_simulations():
        ProjectManager._cached_executions.append(
            functools.partial(ProjectManager._delete_all_simulations)
        )
    
    @staticmethod
    @immediate
    def delete_specific_simulations_immediate(sim_ids):
        ProjectManager._delete_specific_simulations(sim_ids)
    @staticmethod
    def _delete_specific_simulations(sim_ids: Iterable[str]):
        # Clear simulation table
        con, cur = ProjectManager.get_con()
        if (len(sim_ids) < 1):
            return
        ids = set(sim_ids)
        sim_selection_text = " OR ".join(["sim_id=?" for _ in sim_ids])

        # Delete all statuses for each simulation first
        status_delete_text = f"""
        DELETE FROM
            sim_status
        WHERE
            {sim_selection_text}
        """
        cur.execute(status_delete_text, sim_ids)
        logger.info(f"Cleared simulation status from sim_status table")

        # Then delete the simulation information itself
        query_text = f"""
        DELETE FROM
            simulations
        WHERE
            {sim_selection_text}
        """
        cur.execute(query_text, sim_ids)
        con.commit()
        logger.info(f"Cleared simulations '{sim_ids}' from simulations table")

        # Delete all simulation subfolders if possible
        sim_dir_names = [str(id) for id in sim_ids]
        for path in os.listdir(ProjectManager.sims_folder()):
            final_path = os.path.join(ProjectManager.sims_folder(), path)
            if (os.path.isdir(final_path) and os.path.basename(final_path) in sim_dir_names):
                shutil.rmtree(final_path, ignore_errors=True)
                logger.info(f"Cleared simulation subfolder at '{final_path}'")