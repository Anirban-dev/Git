import sys
import argparse
from socketserver import ThreadingMixIn
from http.server import HTTPServer
from .handlers.router import MiniGitRequestHandler
from .config import ensure_storage_dirs

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """
    Multi-threaded HTTP server to process concurrent client commands & git pushes.
    """
    daemon_threads = True

def run_server(host: str = "0.0.0.0", port: int = 3000):
    ensure_storage_dirs()
    server_address = (host, port)
    httpd = ThreadedHTTPServer(server_address, MiniGitRequestHandler)
    print(f"===========================================================")
    print(f" MiniGit Multi-Account Version Control Server v2.0")
    print(f" Listening on http://{host}:{port}")
    print(f" Storage Directory: ./storage/repos/<username>/<repo>")
    print(f"===========================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down MiniGit server...")
        httpd.server_close()
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="MiniGit Protocol & Auth Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=3000, help="Port number (default: 3000)")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port)

if __name__ == "__main__":
    main()
