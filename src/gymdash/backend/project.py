import sqlite3
import os
import pickle
import logging
import argparse
import asyncio
import functools
from threading import Lock
import uuid
from typing import Tuple, List, Any
from datetime import date, datetime
from typing_extensions import Self
from pathlib import Path
from gymdash.backend.core.simulation.base import Simulation

logger = logging.getLogger(__name__)


def uuid2text(id):
    return str(id)
sqlite3.register_adapter(uuid.UUID, uuid2text)
def text2uuid(text):
    return uuid.UUID(text)
sqlite3.register_converter("UUID", text2uuid)

class ProjectManager:

    ARGS_FILENAME = "args.pickle"
    TB_FOLDER = "tb"
    DB_FOLDER = "db"
    DB_NAME = "simulations.db"

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
    def tb_folder():
        return os.path.join(ProjectManager.args.project_dir, ProjectManager.TB_FOLDER)
    @staticmethod
    def db_path():
        return os.path.join(ProjectManager.args.project_dir, ProjectManager.DB_FOLDER, ProjectManager.DB_NAME)

    @staticmethod
    def _setup_project_structure():
        try:
            # Base directory
            path = Path(ProjectManager.args.project_dir)
            path.mkdir(parents=True, exist_ok=True)
            # Sub-dirs
            os.makedirs(os.path.join(path, ProjectManager.TB_FOLDER), exist_ok=True)
            os.makedirs(os.path.join(path, ProjectManager.DB_FOLDER), exist_ok=True)
        except Exception as e:
            logger.error(f"Problem setting up project structure at base directory '{ProjectManager.args.project_dir}'")
            raise e
        
    @staticmethod
    def _setup_database():
        ProjectManager.dbcon = sqlite3.connect(ProjectManager.db_path())
        ProjectManager.dbcur = ProjectManager.dbcon.cursor()
        cur = ProjectManager.dbcur
        cur.execute("""CREATE TABLE IF NOT EXISTS simulations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sim_id UUID,
                    name TEXT,
                    created TIMESTAMP,
                    started TIMESTAMP,
                    ended TIMESTAMP,
                    is_done INTEGER,
                    cancelled INTEGER,
                    failed INTEGER
                    )""")
    
        # cur.execute("INSERT INTO simulations(sim_id, created, started, ended, is_done, cancelled, failed) values (?, ?, ?, ?, ?, ?, ?)", (uuid.uuid4(),   datetime.now(),datetime.now(),datetime.now(),  False, False, False))
        ProjectManager.dbcon.commit()

        # retrieved = cur.execute("SELECT * from simulations").fetchone()
        # print(retrieved)

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
        with ProjectManager._execution_mutex:
            print(f"ProjectManager running {len(ProjectManager._cached_executions)} cached executions")
            for exec_info in ProjectManager._cached_executions:
                exec_info()
                # if (len(exec_info) == 2):
                #     cur.execute(exec_info[0], exec_info[1])
                # else:
                #     cur.execute(exec_info[0])
            ProjectManager._cached_executions.clear()
        con.commit()
        retrieved = cur.execute("SELECT * from simulations").fetchall()
        print(retrieved)


    @staticmethod
    def _add_or_update_simulation(sim_id: uuid.UUID, sim: Simulation):
        con, cur = ProjectManager.get_con()

        check_text = "SELECT COUNT(id) FROM simulations WHERE sim_id=?"
        existing = cur.execute(check_text, (sim_id,)).fetchone()
        print(existing)
        if (existing[0] < 1):
            sim_update_text = """
            INSERT INTO simulations
            (sim_id, name, created, started, ended, is_done, cancelled, failed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                sim_id,
                sim.name,
                sim._meta_create_time,
                sim._meta_start_time,
                sim._meta_end_time,
                sim.is_done,
                sim._meta_cancelled,
                sim._meta_failed
            )
        else:
            sim_update_text = """
            UPDATE simulations
            SET name=?, created=?, started=?, ended=?, is_done=?, cancelled=?, failed=?
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
                sim_id
            )

        cur.execute(sim_update_text, params)


    @staticmethod
    def add_or_update_simulation(sim_id: uuid.UUID, sim: Simulation):
        ProjectManager._cached_executions.append(functools.partial(ProjectManager._add_or_update_simulation, sim_id=sim_id, sim=sim))


        # sim_update_text = """
        # UPDATE simulations
        # SET created=?, started=?, ended=?, is_done=?, cancelled=?, failed=?
        # WHERE sim_id=?
        # """

        # with ProjectManager._execution_mutex:
        #     ProjectManager._cached_executions.append((
        #         sim_update_text,
        #         (
        #             sim._meta_create_time,
        #             sim._meta_start_time,
        #             sim._meta_end_time,
        #             sim.is_done,
        #             sim._meta_cancelled,
        #             sim._meta_failed, sim_id
        #         )
        #     ))



        # con, cur = ProjectManager.get_con(())

        # cur.execute("""
        #             UPDATE simulations
        #             SET created=?, started=?, ended=?, is_done=?, cancelled=?, failed=?
        #             WHERE sim_id=?
        #             """, (
        #                 sim._meta_create_time,
        #                 sim._meta_start_time,
        #                 sim._meta_end_time,
        #                 sim.is_done,
        #                 sim._meta_cancelled,
        #                 sim._meta_failed, sim_id
        #             ))
        # con.commit()

        # retrieved = cur.execute("SELECT * from simulations").fetchall()
        # print(retrieved)