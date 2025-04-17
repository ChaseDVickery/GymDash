import argparse
import os
import subprocess
import http.server
import multiprocessing
import socket
import pickle
import logging
from typing import Callable, Union, List, Tuple, Any
from gymdash.backend.core.api.config.config import set_global_config
from gymdash.backend.project import ProjectManager

logger = logging.getLogger("gymdash")
logger.setLevel(logging.INFO)

# https://stackoverflow.com/questions/2470971/fast-way-to-test-if-a-port-is-in-use-using-python
def socket_used(port) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0
def socket_used_or_invalid(port) -> bool:
    try:
        return socket_used(port)
    except:
        return False
def check_port(port):
    try:
        if socket_used(port):
            print(f"Port {port} is already in use. Choose a different port.")
    except:
        print(f"Problem testing port {port}. Choose a different port.")

# Change JS template to match the input port and address
def setup_frontend(args):
    # Alter the original javascript file to accept the
    # specified API port
    base_path = os.path.dirname(__file__)
    js_main_path    = os.path.join(base_path, "frontend", "scripts", "utils", "api.js")
    js_new_path     = os.path.join(base_path, "frontend", "scripts", "utils", "api_link.js")
    if args.apiserver == "dev":
        final_host = "127.0.0.1"
    elif args.apiserver == "lan":
        # final_host = socket.gethostbyname(socket.gethostname())
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        final_host = s.getsockname()[0]
        s.close()
    elif args.apiserver == "custom_ip":
        final_host = args.apiserver_ip
    logger.info(f"Frontend will query final host at '{final_host}'")
    if (not os.path.exists(js_main_path)):
        logger.error(f"Cannot start frontend because template JS file '{js_main_path}' does not exist")
        return
    else:
        logger.info(f"Modifying API address at {js_main_path} -> {js_new_path}")
        with open(js_main_path, "r") as f:
            new_content = f.read() \
                            .replace(r"<<api_addr>>", "http://" + str(final_host)) \
                            .replace(r"<<api_port>>", str(args.apiport))
            with open(js_new_path, "w") as output_file:
                output_file.write(new_content)

# Creates and returns an HTTP server setup to serve
# the frontend interface
def get_frontend_server(args) -> http.server.HTTPServer:
    HandlerClass = http.server.SimpleHTTPRequestHandler
    # Patch in the correct extensions
    HandlerClass.extensions_map['.js'] = 'application/javascript'
    HandlerClass.extensions_map['.mjs'] = 'application/javascript'
    # HandlerClass.directory = "src/frontend/"
    print(HandlerClass.extensions_map)
    # Run the server (like `python -m http.server` does)
    httpd = http.server.HTTPServer(("localhost", args.port), HandlerClass)
    return httpd

# Starts an HTTP server
def run_frontend_server(args):
    server = get_frontend_server(args)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down HTTP server")
        server.shutdown()

# Starts a subprocess running the Uvicorn FastAPI server
def run_backend_server(args):
    print("Starting API server")
    subprocess.run(["uvicorn", "src.gymdash.backend.main:app", "--host", str(args.apiaddr), "--port", str(args.apiport), "--workers", str(args.apiworkers)])

# Starts the frontend and backend servers
def start(args):
    ProjectManager.export_args(args)
    # Start the servers
    set_global_config(args)
    setup_frontend(args)
    if not args.no_backend:
        check_port(args.port)
        multiprocessing.Process(target=run_backend_server, args=(args,)).start()
    if not args.no_frontend:
        check_port(args.apiport)
        multiprocessing.Process(target=run_frontend_server, args=(args,)).start()

def add_gymdash_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("-d", "--project-dir",  default="./.gymdash-projects", type=str, help="Base relative path for the GymDash project")
    parser.add_argument("-p", "--port",         default=8888, type=int, help="Port for frontend interface")
    parser.add_argument("-b", "--apiport",      default=8887, type=int, help="Port for backend API")
    parser.add_argument("-a", "--apiaddr",      default="127.0.0.1", type=str, help="Address for backend API")
    parser.add_argument("-w", "--apiworkers",   default=1, type=int, help="Number of workers for backend API")
    parser.add_argument("--apiserver",          default="dev", choices=["dev", "lan", "custom_ip"], help="How the API should be exposed. dev=only exposed to localhost (127.0.0.1). lan=local IPv4 address (usually 192.168.x.xxx). custom_ip=specify the address that the frontend should query for API access.")
    parser.add_argument("--apiserver-ip",       default="127.0.0.1", type=str, help="The custom IP address through which the API should be accessible.")
    parser.add_argument("--no-frontend",        action="store_true", help="Run without the frontend display")
    parser.add_argument("--no-backend",         action="store_true", help="Run without the backend API server")
    return parser


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
                    prog='GymDash',
                    description='Start GymDash environment and frontend',
                    epilog='Text at the bottom of help')
    parser = add_gymdash_arguments(parser)
    args = parser.parse_args()

    start(args)