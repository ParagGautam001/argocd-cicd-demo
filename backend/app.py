from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        self.wfile.write(
            b'{"message":"Hello from Backend","version":"v1"}'
        )

server = HTTPServer(("0.0.0.0", 8080), Handler)

print("Backend running on port 8080")

server.serve_forever()