
import os
import importlib
import sys
import pickle
import types
import inspect
import logging
import json
from typing import Set, Dict, Tuple, Any, List
from pathlib import Path
from gymdash.backend.core.simulation.base import SimulationRegistry

logger = logging.getLogger(__name__)

class SimulationExporter:

    DEFAULT_MODULE_NAME = "gymdash_default_sim_export_module"
    IMPORT_INDEX_FILENAME = "import.json"
    EXPORTED_SIM_FILENAME = "exported_simulations.pickle"

    import_index: Set[str] = set()
    # simulation_packages: Dict[str, Tuple[str, types.ModuleType]] = {}
    simulations: Dict[str, Any] = {}
    # simulations: List[Tuple[str, Any]] = {}

    _import_index_imported: Set[str] = set()
    _simulations_imported: Dict[str, Any] = {}

    @staticmethod
    def _get_export_folder() -> Path:
        path = Path(os.path.dirname(__file__), "exported_sims")
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Could not create simulation export folder")
        return path

    # @staticmethod
    # def prepare_for_export(sim_key, sim_type, sim_file_path, module_name=DEFAULT_MODULE_NAME):
    #     # Find relevant module with the module name
    #     # or create a new module type using module name
    #     if module_name in SimulationExporter.simulation_packages:
    #         module = SimulationExporter.simulation_packages[module_name]
    #     else:
    #         module = types.ModuleType(module_name)
    #         SimulationExporter.simulation_packages[module_name] = module
    #     # Try to find the class name in the current module.
    #     # If it already exists in the current module, then we have a problem.
    #     sim_type_name = sim_type.__name__            
    #     try:
    #         _ = module.__getattr__(sim_type_name)
    #         class_already_in_module = True
    #     except AttributeError:
    #         class_already_in_module = False
    #     if (class_already_in_module):
    #         logger.warning(f"Could not add simulation '{sim_type}' to module '{module_name}' because it already exists in '{module_name}'")
    #         return False
    #     # Now, just try to add the class to the module
    #     # and set the class's module to the module's name
    #     module.__setattr__(sim_type_name, sim_type)
    #     sim_type.__module__ = module_name
    #     SimulationExporter.import_index.add(sim_file_path)
    #     # Success!
    #     return True

    @staticmethod
    def prepare_for_export(sim_key, sim_type):
        # Find relevant module with the module name
        # or create a new module type using module name
        if sim_key in SimulationExporter.simulations:
            logger.warning(f"Could not prepare simulation '{sim_type}' for export because it uses already-exported key '{sim_key}'")
            return False
        # Add file to import to be able to use the Simulation
        try:
            sim_file_path = inspect.getfile(sim_type)
        except:
            logger.warning(f"Could not prepare simulation '{sim_type}' for export because the source file for the type could not be inspected.")
            return False
        SimulationExporter.simulations[sim_key] = sim_type
        SimulationExporter.import_index.add(sim_file_path)
        # Success!
        return True
        
    @staticmethod
    def export_sims():
        """
        Exports prepared simulation types and their modules to a pickle
        file to be imported by the Uvicorn/FastAPI backend setup. This is
        because uvicorn is being run as a subprocess and does not use the
        launching script's memory space, so all custom Simulation types that
        should be accessible by the API should be exported.
        """
        export_folder = SimulationExporter._get_export_folder()
        index_filepath = os.path.join(export_folder, SimulationExporter.IMPORT_INDEX_FILENAME)
        exported_filepath = os.path.join(export_folder, SimulationExporter.EXPORTED_SIM_FILENAME)
        # Try to export index
        try:
            with open(index_filepath, "w") as f:
                json.dump(list(SimulationExporter.import_index), f)
        except Exception as e:
            logger.exception(f"Exception while exporting SimulationExporter index file to '{index_filepath}'")
            return False
        # Try to export all the Simulation type information
        try:
            with open(exported_filepath, "wb") as f:
                pickle.dump(SimulationExporter.simulations, f)
        except Exception as e:
            logger.exception(f"Exception while exporting Simulation types to '{exported_filepath}'")
            return False
        logger.info(f"Successfully exported {len(SimulationExporter.simulations)} simulation types and {len(SimulationExporter.import_index)} import files.")
        return True
    
    @staticmethod
    def import_from_path(module_name, file_path):
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def import_and_register():
        export_folder = SimulationExporter._get_export_folder()
        index_filepath = os.path.join(export_folder, SimulationExporter.IMPORT_INDEX_FILENAME)
        exported_filepath = os.path.join(export_folder, SimulationExporter.EXPORTED_SIM_FILENAME)
        # Try to read in exported files
        if not os.path.exists(index_filepath):
            logger.error(f"SimulationExporter cannot import_and_register because index file at '{index_filepath}' does not exist.")
            return False
        if not os.path.exists(exported_filepath):
            logger.error(f"SimulationExporter cannot import_and_register because Simulation types file at '{index_filepath}' does not exist.")
            return False
        try:
            with open(index_filepath, "r") as f:
                SimulationExporter._import_index_imported = set(json.load(f))
        except Exception as e:
            logger.exception(f"Exception while reading index file from '{index_filepath}'")
            return False
        try:
            with open(exported_filepath, "rb") as f:
                SimulationExporter._simulations_imported = pickle.load(f)
        except Exception as e:
            logger.exception(f"Exception while reading Simulation types file from '{exported_filepath}'")
            return False
        # Now attempt to actually load the modules and register the Simulations
        for load_filepath in SimulationExporter._import_index_imported:
            imported_module = SimulationExporter.import_from_path(SimulationExporter.DEFAULT_MODULE_NAME, load_filepath)
        for sim_key, sim_type in SimulationExporter._simulations_imported.items():
            SimulationRegistry.register(sim_key, sim_type)
        logger.info(f"Successfully imported {len(SimulationExporter._simulations_imported)} simulation types and {len(SimulationExporter._import_index_imported)} import files.")
        return True