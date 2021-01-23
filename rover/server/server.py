#!/usr/bin/python

import logging
import socketserver
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Tuple, Optional
from urllib.parse import urlparse

from doltpy.core import Dolt
from doltpy.core.system_helpers import get_logger

from archiver import config
from config import config as main_config
import rover.server.page_handler as handler
import rover.server.api_handler as api
import rover.server.schema_handler as schema

threadLock: threading.Lock = threading.Lock()


class WebServer(threading.Thread):
    def __init__(self, threadID: int, name: str):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name

        self.logger: logging.Logger = get_logger(__name__)
        self.INFO_QUIET: int = main_config.INFO_QUIET
        self.VERBOSE: int = main_config.VERBOSE

        self.host_name = "0.0.0.0"
        self.port = 8930

    def run(self):
        self.logger.log(self.INFO_QUIET, "Starting " + self.name)

        # Get lock to synchronize threads
        threadLock.acquire()

        webServer = HTTPServer((self.host_name, self.port), RequestHandler)
        self.logger.log(self.INFO_QUIET, "Server Started %s:%s" % (self.host_name, self.port))

        try:
            webServer.serve_forever()
        except KeyboardInterrupt as e:
            raise e  # TODO: Figure Out How To Prevent Need To Kill Twice

        webServer.server_close()
        self.logger.log(self.INFO_QUIET, "Server Stopped")

        # Free lock to release next thread
        threadLock.release()


class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, request: bytes, client_address: Tuple[str, int], server: socketserver.BaseServer):
        self.logger: logging.Logger = get_logger(__name__)
        self.INFO_QUIET: int = main_config.INFO_QUIET
        self.VERBOSE: int = main_config.VERBOSE

        # TODO: Implement Global Handle On Repo
        # Initiate Repo For Server
        self.repo: Optional[Dolt] = None
        self.initRepo(path=config.ARCHIVE_TWEETS_REPO_PATH,
                      create=False,
                      url=config.ARCHIVE_TWEETS_REPO_URL)

        super().__init__(request, client_address, server)

    def initRepo(self, path: str, create: bool, url: str = None):
        # Prepare Repo For Data
        if create:
            repo = Dolt.init(path)
            repo.remote(add=True, name='origin', url=url)
            self.repo: Dolt = repo

        self.repo: Dolt = Dolt(path)

    def log_message(self, log_format: str, *args: [str]):
        self.logger.log(logging.DEBUG, log_format % args)

    def do_POST(self):
        url: str = urlparse(self.path).path.rstrip('/').lower()

        try:
            if url.startswith("/api"):
                api.handle_api(self=self)
            else:
                handler.load_404_page(self=self)
        except BrokenPipeError as e:
            self.logger.debug("{ip_address} Requested {page_url}: {error_message}".format(ip_address=self.address_string(), page_url=self.path, error_message=e))

    def do_GET(self):
        url: str = urlparse(self.path).path.rstrip('/').lower()

        try:
            if url.startswith("/api"):
                api.handle_api(self=self)
            # elif url.startswith("/schema"):
            #     schema.handle_schema(self=self)
            if url.startswith("/tweet"):
                handler.load_tweet(self=self)
            elif url == "":
                handler.load_page(self=self, page='latest-tweets')
            elif url == "/manifest.webmanifest":
                handler.load_file(self=self, path="rover/server/web/other/manifest.json", mime_type="application/manifest+json")
            elif url == "/robots.txt":
                handler.load_file(self=self, path="rover/server/web/other/robots.txt", mime_type="text/plain")
            elif url == "/favicon.ico":
                handler.load_404_page(self=self)
            elif url == "/images/rover-twitter-card.png":
                handler.load_file(self=self, path="rover/server/web/images/Rover.png", mime_type="image/png")
            elif url == "/images/rover.png":
                handler.load_file(self=self, path="rover/server/web/images/Rover.png", mime_type="image/png")
            elif url == "/images/rover.svg":
                handler.load_file(self=self, path="rover/server/web/images/Rover.svg", mime_type="image/svg+xml")
            elif url == "/css/stylesheet.css":
                handler.load_file(self=self, path="rover/server/web/css/stylesheet.css", mime_type="text/css")
            elif url == "/scripts/main.js":
                handler.load_file(self=self, path="rover/server/web/scripts/main.js", mime_type="application/javascript")
            elif url == "/scripts/helper.js":
                handler.load_file(self=self, path="rover/server/web/scripts/helper.js", mime_type="application/javascript")
            elif url == "/service-worker.js":
                handler.load_file(self=self, path="rover/server/web/scripts/service-worker.js", mime_type="application/javascript")
            elif url == "/404":
                handler.load_404_page(self=self, error_code=200)
            elif url == "/offline":
                handler.load_offline_page(self=self)
            else:
                handler.load_404_page(self=self)
        except BrokenPipeError as e:
            self.logger.debug("{ip_address} Requested {page_url}: {error_message}".format(ip_address=self.address_string(), page_url=self.path, error_message=e))

    def version_string(self):
        return "Rover"
