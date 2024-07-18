import json
import random
import datetime
from http.server import SimpleHTTPRequestHandler, HTTPServer

# Function to generate random floats
def generate_random_floats(num):
    return [random.uniform(0, 100) for _ in range(num)]

# Function to generate random date-time values
def generate_random_dates(num, start_date):
    dates = []
    previous_date = start_date
    for i in range(num):
        current_date = previous_date + datetime.timedelta(minutes=random.uniform(5, 15))
        previous_date = current_date
        dates.append(current_date)
    #dates = [start_date + datetime.timedelta(minutes=random.uniform(5, 15) * i) for i in range(num)]
    return dates

# Generate a list of lists with random floats
data = [generate_random_floats(10) for _ in range(10)]

# Generate labels for each list in reverse order
labels = [f"Chart {i + 1}" for i in range(len(data))][::-1]

# Generate random start dates for each list and generate date-time index labels
start_date = datetime.datetime.now() - datetime.timedelta(days=1)
index_labels = [generate_random_dates(10, start_date + datetime.timedelta(minutes=50 * i)) for i in range(len(data))]

class RequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/random-floats':
            # Create a response object containing data and labels
            response = {
                'data': data,
                'labels': labels,
                'index_labels': [[date.strftime('%Y-%m-%d %H:%M:%S') for date in dates] for dates in index_labels]
            }
            # Convert the response object to JSON
            response_json = json.dumps(response)
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(response_json.encode())
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
