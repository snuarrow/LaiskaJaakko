import json
import random
from http.server import SimpleHTTPRequestHandler, HTTPServer

# Generate a list of lists with random floats
data = [[random.uniform(0, 100) for _ in range(10)] for _ in range(10)]

class RequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/random-floats':
            # Convert the entire data list to JSON
            response = json.dumps(data)
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(response.encode())
        else:
            # Serve static files
            super().do_GET()

# Define server address and port
server_address = ('', 8000)

# Create the HTTP server
httpd = HTTPServer(server_address, RequestHandler)

# Print server details
print(f"Serving on port {server_address[1]}...")

# Start the server
httpd.serve_forever()
