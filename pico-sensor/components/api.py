from microdot import Microdot, Response

# Initialize the Microdot app
app = Microdot()
CHUNK_SIZE = 1024

@app.route('/')
def index(request):
    with open('/dist/index.html') as f:
        return f.read(), 200, {'Content-Type': 'text/html'}


@app.route('/<path:path>')
def static(request, path):
    file_path = f'/dist/{path}'
    # Set correct MIME types for different files
    if path.endswith('.js'):
        content_type = 'application/javascript'
    elif path.endswith('.css'):
        content_type = 'text/css'
    elif path.endswith('.html'):
        content_type = 'text/html'
    else:
        content_type = 'application/octet-stream'
    
    return serve_file(file_path, content_type)


def serve_file(file_path, content_type):
    def file_stream():
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk
    
    return Response(body=file_stream(), headers={'Content-Type': content_type})


# Run the app
app.run(host='0.0.0.0', port=8080)
