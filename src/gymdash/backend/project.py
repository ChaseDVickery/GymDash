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
from typing import Any, List, Tuple

from typing_extensions import Self

from gymdash.backend.core.api.models import (SimulationStartConfig,
                                             StoredSimulationInfo)
from gymdash.backend.core.simulation.base import Simulation

logger = logging.getLogger(__name__)


def uuid2text(id: uuid.UUID):
    return str(id)
def config2text(config: SimulationStartConfig):
    return json.dumps(config, cls=SimulationStartConfig.Encoder)
sqlite3.register_adapter(uuid.UUID, uuid2text)
sqlite3.register_adapter(SimulationStartConfig, config2text)
sqlite3.register_adapter(bool, int)
# Converter objects are always passed a bytes object, so handle that
def text2uuid(byte_text):
    text = byte_text.decode("utf-8")
    return uuid.UUID(text)
def text2config(byte_text):
    text = byte_text.decode("utf-8")
    return json.loads(text, object_hook=SimulationStartConfig.custom_decoder)
sqlite3.register_converter("UUID", text2uuid)
sqlite3.register_converter("SIMULATIONCONFIG", text2config)
sqlite3.register_converter("BOOL", lambda i: bool(int(i)))

class ProjectManager:

    ARGS_FILENAME   = "args.pickle"
    TB_FOLDER       = "tb"
    SIMS_FOLDER     = "sims"
    DB_FOLDER       = "db"
    DB_NAME         = "simulations.db"

    _execution_mutex = Lock()
    _cached_executions: List[Tuple[str, Any]] = []

    @staticmethod
    def get_con() -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
        return ProjectManager.dbcon, ProjectManager.dbcur

    @staticmethod
    def setup_from_args(args):
        ProjectManager.args = args
        ProjectManager.dbcon = None
        ProjectManager.dbcur = None
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
        ProjectManager.dbcur = ProjectManager.dbcon.cursor()
        ProjectManager._create_simulations_table()

    @staticmethod
    def _create_simulations_table():
        con, cur = ProjectManager.get_con()
        cur = ProjectManager.dbcur
        cur.execute("""CREATE TABLE IF NOT EXISTS simulations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sim_id UUID,
                    name TEXT,
                    created TIMESTAMP,
                    started TIMESTAMP,
                    ended TIMESTAMP,
                    is_done BOOL,
                    cancelled BOOL,
                    failed BOOL,
                    config SIMULATIONCONFIG
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
        except:
            ProjectManager._execution_mutex.release()
        con.commit()

        # ProjectManager.get_filtered_simulations()
        # retrieved = cur.execute("SELECT * from simulations").fetchall()
        # print(retrieved)


    @staticmethod
    def _add_or_update_simulation(sim_id: uuid.UUID, sim: Simulation):
        if sim is None: return
        con, cur = ProjectManager.get_con()

        check_text = "SELECT COUNT(id) FROM simulations WHERE sim_id=?"
        existing = cur.execute(check_text, (sim_id,)).fetchone()
        print(existing)
        if (existing[0] < 1):
            sim_update_text = """
            INSERT INTO simulations
            (sim_id, name, created, started, ended, is_done, cancelled, failed, config)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                sim.config,
            )
        else:
            sim_update_text = """
            UPDATE simulations
            SET name=?, created=?, started=?, ended=?, is_done=?, cancelled=?, failed=?, config=?
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
                sim.config,
                sim_id
            )

        cur.execute(sim_update_text, params)

    @staticmethod
    def add_or_update_simulation(sim_id: uuid.UUID, sim: Simulation):
        ProjectManager._cached_executions.append(
            functools.partial(ProjectManager._add_or_update_simulation, sim_id=sim_id, sim=sim)
        )

    @staticmethod
    def get_filtered_simulations(
        started:datetime=None,
        ended:datetime=None,
        done:bool=None,
        cancelled:bool=None,
        failed:bool=None,
    ) -> List[StoredSimulationInfo]:
        con, cur = ProjectManager.get_con()

        query_text = """
        SELECT
            sim_id, name, created, started, ended, is_done, cancelled, failed, config
        FROM
            simulations
        ORDER BY
            created ASC
        """
        cur.execute(query_text)

        res = cur.fetchall()
        results = []
        for info in res:
            results.append(
                StoredSimulationInfo(
                    sim_id      = info[0],
                    name        = info[1],
                    created     = info[2],
                    started     = info[3],
                    ended       = info[4],
                    is_done     = info[5],
                    cancelled   = info[6],
                    failed      = info[7],
                    config      = info[8]
                )
            )
        logger.error(f"Got {len(results)} db results")
        return results
    
    @staticmethod
    def delete_all_simulations_immediate():
        # Run cached executions early so we don't
        # immediately repopulate with old stuff
        ProjectManager.run_cached_executions()
        with ProjectManager._execution_mutex:
            ProjectManager._delete_all_simulations()
    @staticmethod
    def _delete_all_simulations():
        # Clear simulation table
        con, cur = ProjectManager.get_con()
        cur.execute("DROP TABLE simulations")
        ProjectManager._create_simulations_table()
        con.commit()
        logger.info("Cleared table 'simulations'")
        # Delete all simulation subfolders if possible
        shutil.rmtree(ProjectManager.sims_folder(), ignore_errors=True)
        ProjectManager._setup_project_structure()
        logger.info(f"Cleared simulation subfolder at '{ProjectManager.sims_folder()}'")
    @staticmethod
    def delete_all_simulations():
        ProjectManager._cached_executions.append(
            functools.partial(ProjectManager._delete_all_simulations)
        )