import argparse
import uvicorn
import os
import asyncio
import socketserver
import subprocess
import signal
import http.server
import multiprocessing
from threading import Thread, current_thread
from src.scripts.start_utils import Server


parser = argparse.ArgumentParser(
                    prog='GymDash',
                    description='Start GymDash environment and frontend',
                    epilog='Text at the bottom of help')
# Frontend port
parser.add_argument("-p", "--port", default=8888, type=int, help="Port for frontend interface")
# Backend port
parser.add_argument("-b", "--apiport", default=8887, type=int, help="Port for backend API")
parser.add_argument("-a", "--apiaddr", default="127.0.0.1", type=str, help="Address for backend API")
parser.add_argument("-w", "--apiworkers", default=1, type=int, help="Number of workers for backend API")

args = parser.parse_args()



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

# Start API server
def setup_frontend(args):
    # Alter the original javascript file to accept the
    # specified API port
    js_main_path    = os.path.join("src", "frontend", "scripts", "gymdash.js")
    js_new_path     = os.path.join("src", "frontend", "scripts", "gymdash_link.js")
    if (not os.path.exists(js_main_path)):
        print(f"Cannot start frontend because template JS file '{js_main_path}' does not exist")
        return
    else:
        with open(js_main_path, "r") as f:
            new_content = f.read() \
                            .replace(r"apiAddr = \"http://127.0.0.1\";", "apiAddr = \"" + args.apiaddr + "\";") \
                            .replace(r"apiPort = 8000;", "apiPort = " + str(args.apiport) + ";")
            with open(js_new_path, "w") as output_file:
                output_file.write(new_content)

def setup_backend_server(args) -> uvicorn.Server:
    config = uvicorn.Config("src.api.api:app", port=args.apiport, workers=args.apiworkers, log_level="info")
    # server = uvicorn.Server(config)
    server = Server(config)
    return server
    # await server.serve()
    # uvicorn.run("src.api.api:app", port=args.apiport, workers=args.apiworkers)

# Start frontend HTTP server
def setup_frontend_server(args) -> http.server.HTTPServer:
    import http.server

    HandlerClass = http.server.SimpleHTTPRequestHandler
    # Patch in the correct extensions
    HandlerClass.extensions_map['.js'] = 'application/javascript'
    HandlerClass.extensions_map['.mjs'] = 'application/javascript'
    HandlerClass.directory = "src/frontend/"
    # Run the server (like `python -m http.server` does)
    httpd = http.server.HTTPServer(("localhost", args.port), HandlerClass)
    return httpd
    # try:
    #     httpd.serve_forever()
    # except KeyboardInterrupt:
    #     print("\nStopping server...")
    #     httpd.shutdown()
    #     print("Server stopped.")

def run_backend_server(server:uvicorn.Server):
    print("Starting API server")
    asdf = setup_backend_server(args)
    try:
        asdf.run()
    except KeyboardInterrupt:
        print("Shutting down API server")
        asdf.shutdown()
def run_frontend_server(server:http.server.HTTPServer):
    print("Starting HTTP server")
    asdf = setup_frontend_server(args)
    try:
        asdf.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down HTTP server")
        asdf.shutdown()

t1 = None
t2 = None
api_server = None
frontend_server = None

async def something(args):
    global t1
    global t2
    global api_server
    global frontend_server
    setup_frontend(args)
    api_server = setup_backend_server(args)
    frontend_server = setup_frontend_server(args)
    # t1 = Thread(target=run_backend_server, args=[api_server])
    # t2 = Thread(target=run_frontend_server, args=[frontend_server])
    t1 = multiprocessing.Process(target=run_backend_server, args=(None, ))
    t2 = multiprocessing.Process(target=run_frontend_server, args=(None, ))
    t1.start()
    t2.start()
    while True:
        try:
            await asyncio.sleep(0)
        except KeyboardInterrupt:
            print("ENDING??????????")
            os.kill(os.getpid(), signal.SIGTERM)
            # api_server.shutdown()
            frontend_server.shutdown()
            t1.join()
            t2.join()
            exit()

    # with api_server.run_in_thread(args):
    #     # t1 = Thread(target=run_backend_server, args=[api_server])
    #     t2 = Thread(target=run_frontend_server, args=[frontend_server])
    #     # t1.start()
    #     t2.start()
    #     while True:
    #         await asyncio.sleep(0)

def start(args):
    global t1
    global t2
    global api_server
    global frontend_server
    try:
        asyncio.run(something(args))
    except KeyboardInterrupt:
        # frontend_server.shutdown()
        # api_server.shutdown()
        t1.terminate()
        t2.terminate()
        t1.join()
        t2.join()
        exit()
    # asyncio.run(something(args))

    # setup_frontend(args)
    # api_server = setup_backend_server(args)
    # frontend_server = setup_frontend_server(args)
    # with api_server.run_in_thread(args):
    #     # t1 = Thread(target=run_backend_server, args=[api_server])
    #     t2 = Thread(target=run_frontend_server, args=[frontend_server])
    #     # t1.start()
    #     t2.start()
    # print("Press Ctrl+C to exit...")

    # while(True):
    #     try:
    #         pass
    #     except KeyboardInterrupt:
    #         print("bruh")
    #         os.kill(os.getpid(), signal.SIGTERM)
    #         # api_server.shutdown()
    #         # print("Called shutdown on API server")
    #         # frontend_server.shutdown()
    #         # print("Called shutdown on HTTP server")
    #         # t1.join()
    #         # t2.join()

def a():
    subprocess.run(["uvicorn", "src.api.api:app", "--host", str(args.apiaddr), "--port", str(args.apiport), "--workers", str(args.apiworkers)])
def b():
    run_frontend_server(None)
    # subprocess.run(["python", "testserve.py"])

if __name__ == "__main__":
    # Check if ports are open
    try:
        if socket_used(args.port):
            print(f"Frontend port {args.port} is already in use. Choose a different port.")
    except:
        print(f"Problem testing frontend port {args.port}. Choose a different port.")
    try:
        if socket_used(args.apiport):
            print(f"API port {args.apiport} is already in use. Choose a different port.")
    except:
        print(f"Problem testing API port {args.apiport}. Choose a different port.")

    # asyncio.run(start_backend(args))
    # print("Here")
        
    # start(args)

    setup_frontend()
    multiprocessing.Process(target=a).start()
    multiprocessing.Process(target=b).start()

    # setup_frontend(args)

    # start_frontend(args)
    # asyncio.run(start_backend(args))

    # Thread(target=start_frontend, args=[args]).start()
    # Thread(target=start_backend, args=[args]).start()



    # start_frontend(args)
    # start_backend(args)