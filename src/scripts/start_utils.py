import contextlib
import time
import threading
import uvicorn

# https://stackoverflow.com/questions/61577643/python-how-to-use-fastapi-and-uvicorn-run-without-blocking-the-thread
class Server(uvicorn.Server):
    def install_signal_handlers(self):
        pass

    @contextlib.contextmanager
    def run_in_thread(self, args):
        thread = threading.Thread(target=self.run)
        thread.start()
        try:
            while not self.started:
                time.sleep(1e-3)
            yield
        finally:
            self.should_exit = True
            thread.join()

# config = uvicorn.Config("example:app", host="127.0.0.1", port=5000, log_level="info")
# server = Server(config=config)

# with server.run_in_thread():
    # Server is started.
    ...
    # Server will be stopped once code put here is completed
    ...

# Server stopped.
