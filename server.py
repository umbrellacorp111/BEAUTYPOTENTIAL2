import asyncio
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from bot.main import main as bot_main

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        logger.info("HTTP: %s", format % args)


def run_http_server():
    server = HTTPServer(("0.0.0.0", 3000), HealthHandler)
    logger.info("Healthcheck HTTP server started on port 3000")
    server.serve_forever()


if __name__ == "__main__":
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    asyncio.run(bot_main())
