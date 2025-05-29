from http.server import SimpleHTTPRequestHandler, HTTPServer
import os
import json

class MyHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/clear.json":
            with open("job_data.json", "w") as f:
                json.dump({}, f)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Cleared")
        else:
            self.send_error(404)

if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    HTTPServer(("localhost", 8080), MyHandler).serve_forever()
