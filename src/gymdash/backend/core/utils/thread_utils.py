import threading
import queue
import logging

queued = queue.Queue()
logger = logging.getLogger(__name__)

def run_on_main_thread(func, *args, **kwargs):
    queued.put(lambda: func(*args, **kwargs))

def execute_queued():
    if threading.current_thread() is threading.main_thread():
        while queued.qsize() != 0:
            callback = queued.get()
            try:
                callback()
            except Exception as e:
                logger.error(f"FUNCTION QUEUED TO RUN ON MAIN THREAD FAILED WITH ERROR: {e}")
    else:
        logger.warning("execute_queued should only be invoked from the main thread.")
