import json
import random
import sys
import os
import time
from http.server import SimpleHTTPRequestHandler, HTTPServer
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class RequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/random-floats':
            # Generate a list of random floats
            random_floats = [random.uniform(0, 1) for _ in range(100)]
            # Convert the list to JSON
            response = json.dumps(random_floats)
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(response.encode())
        else:
            # Serve static files
            super().do_GET()

class ChangeHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.event_type in ('modified', 'created', 'deleted'):
            print("Changes detected, restarting server...")
            os.execv(sys.executable, ['python'] + sys.argv)

def run_server():
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"Serving on port {server_address[1]}...")
    httpd.serve_forever()

if __name__ == '__main__':
    observer = Observer()
    event_handler = ChangeHandler()
    observer.schedule(event_handler, path='.', recursive=True)
    observer.start()

    try:
        run_server()
    except KeyboardInterrupt:
        observer.stop()
    observer.join()