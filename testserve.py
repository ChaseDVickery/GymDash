# https://stackoverflow.com/questions/63166774/how-can-i-use-es6-modules-on-python-http-server

import http.server

HandlerClass = http.server.SimpleHTTPRequestHandler

# Patch in the correct extensions
HandlerClass.extensions_map['.js'] = 'application/javascript'
HandlerClass.extensions_map['.mjs'] = 'application/javascript'

print(HandlerClass.extensions_map)

# Run the server (like `python -m http.server` does)
httpd = http.server.HTTPServer(("0.0.0.0", 8888), HandlerClass)
httpd.serve_forever()