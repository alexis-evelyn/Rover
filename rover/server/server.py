#!/usr/bin/python
import json
import re
import logging
import socketserver
import string
import threading
import uuid
import IP2Location
import IP2Proxy

import sqlalchemy

import rover.server.page_handler as handler
import rover.server.api_handler as api
import rover.server.schema_handler as schema
import pandas as pd

from sqlalchemy import create_engine
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Tuple, Optional, List
from urllib.parse import urlparse, parse_qs
from functools import partial
from anonymizeip import anonymize_ip

from doltpy.core import Dolt, ServerConfig
from doltpy.core.system_helpers import get_logger
from mysql.connector import conversion

from archiver import config as archiver_config
from rover import config as rover_config
from config import config as main_config

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

        # TODO: Implement Global Handle On Repo
        # Initiate Repo For Server
        self.repo: Optional[Dolt] = None
        self.initRepo(path=archiver_config.ARCHIVE_TWEETS_REPO_PATH,
                      create=False,
                      url=archiver_config.ARCHIVE_TWEETS_REPO_URL)

        # Setup Analytics SQL Server
        self.analytics_server_config: ServerConfig = ServerConfig(port=rover_config.ANALYTICS_PORT)
        self.analytics_repo: Optional[Dolt] = Dolt(repo_dir=rover_config.ANALYTICS_REPO_PATH,
                                                   server_config=self.analytics_server_config)

        # Start Analytics SQL Server
        self.analytics_repo.sql_server()
        self.analytics_engine: sqlalchemy.engine = create_engine(f"mysql://{rover_config.ANALYTICS_USERNAME}@{rover_config.ANALYTICS_HOST}:{rover_config.ANALYTICS_PORT}/{rover_config.ANALYTICS_DATABASE}", echo=False)

        # Setup Web/Rover Config
        with open(rover_config.CONFIG_FILE_PATH, "r") as file:
            self.config: dict = json.load(file)

        self.ip_lookup: IP2Location = IP2Location.IP2Location(filename=rover_config.IP_DATABASE, mode="SHARED_MEMORY")
        self.proxy_lookup: IP2Proxy = IP2Proxy.IP2Proxy(filename=rover_config.PROXY_DATABASE)

        self.logger.log(self.VERBOSE, "Starting Web Server!!!")

    def initRepo(self, path: str, create: bool, url: str = None):
        # Prepare Repo For Data
        if create:
            repo = Dolt.init(path)
            repo.remote(add=True, name='origin', url=url)
            self.repo: Dolt = repo

        self.repo: Dolt = Dolt(repo_dir=path)

    def run(self):
        self.logger.log(self.INFO_QUIET, "Starting " + self.name)

        # Get lock to synchronize threads
        threadLock.acquire()

        requestHandler: partial = partial(RequestHandler, self.analytics_engine, self.repo, self.config, self.ip_lookup, self.proxy_lookup)
        webServer = HTTPServer((self.host_name, self.port), requestHandler)
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
    def __init__(self, analytics_engine: sqlalchemy.engine, repo: Dolt, config: dict, ip_lookup: IP2Location, proxy_lookup: IP2Proxy, request: bytes, client_address: Tuple[str, int], server: socketserver.BaseServer):
        self.logger: logging.Logger = get_logger(__name__)
        self.INFO_QUIET: int = main_config.INFO_QUIET
        self.VERBOSE: int = main_config.VERBOSE

        self.config: dict = config
        self.repo: Dolt = repo
        self.analytics_engine: sqlalchemy.engine = analytics_engine
        self.ip_lookup: IP2Location = ip_lookup
        self.proxy_lookup: IP2Proxy = proxy_lookup

        self.logger.log(self.VERBOSE, "Starting Request Handler!!!")

        super().__init__(request, client_address, server)

    def log_message(self, log_format: str, *args: [str]):
        self.logger.log(logging.DEBUG, log_format % args)

    def do_POST(self):
        queries: dict[str, list[str]] = parse_qs(urlparse(self.path).query)
        url: str = urlparse(self.path).path.rstrip('/').lower()

        self.log_web_request(queries=queries)

        try:
            if url.startswith("/api"):
                api.handle_api(self=self)
            else:
                handler.load_404_page(self=self)
        except BrokenPipeError as e:
            self.logger.debug("{ip_address} Requested {page_url}: {error_message}".format(ip_address=self.address_string(), page_url=self.path, error_message=e))

    def do_GET(self):
        queries: dict[str, list[str]] = parse_qs(urlparse(self.path).query)
        url: str = urlparse(self.path).path.rstrip('/').lower()

        self.log_web_request(queries=queries)

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
            elif url.startswith("/sitemap") and url.endswith(".xml"):
                handler.load_sitemap(self=self)
            elif url == "/404":
                handler.load_404_page(self=self, error_code=200)
            elif url == "/offline":
                handler.load_offline_page(self=self)
            else:
                handler.load_404_page(self=self)
        except BrokenPipeError as e:
            self.logger.debug("{ip_address} Requested {page_url}: {error_message}".format(ip_address=self.address_string(), page_url=self.path, error_message=e))

    def log_web_request(self, queries: dict[str, list[str]]):
        try:
            filtered_queries = filter(lambda elem: str(elem[0]).startswith("utm_"), queries.items())
            tracking_parameters: dict[str, list[str]] = dict(filtered_queries)

            # Print URL Path If UTM Tracking Applied
            if len(tracking_parameters) > 0:
                self.logger.debug(f"UTM Path: {urlparse(self.path).path}")

            # Store Valid UTM In Dict For Logging
            utm_parameters: dict = {}

            # Print UTM Queries
            for track in tracking_parameters:
                param_name: str = track.rsplit('_')[1].capitalize()

                # We Don't Bother With `utm_` Without Anything After The Dash
                if param_name.strip() == "":
                    continue

                utm_value: list = tracking_parameters[track]
                utm_parameters[param_name.lower()] = ", ".join(utm_value)
                self.logger.debug(f"UTM {param_name}: {', '.join(utm_value)}")

            # Add In Hardcoded Cells
            current_time: datetime = datetime.now(timezone.utc)
            utm_parameters["path"]: str = urlparse(self.path).path
            utm_parameters["date"]: str = "{year}-{month}-{day} {hour}:{minute}:{second}".format(
                year=str(current_time.year).zfill(4), month=str(current_time.month).zfill(2), day=str(current_time.day).zfill(2),
                hour=str(current_time.hour).zfill(2), minute=str(current_time.minute).zfill(2), second=str(current_time.second).zfill(2)
            )

            # Add Referer
            if "referer" in self.headers:
                utm_parameters["referer"]: str = self.headers["referer"]

            if "cookie" in self.headers:
                cookies_split: List[str] = self.headers['cookie'].split('; ')
                cookies: dict = {}

                for cookie_split in cookies_split:
                    cookie: List[str] = cookie_split.split('=')
                    cookies[cookie[0]] = cookie[1]

                if 'analytics' in cookies:
                    utm_parameters["tracker"]: str = cookies['analytics']

                if 'session' in cookies:
                    utm_parameters["tracking_session"]: str = cookies['session']

            # Languages of Users (To Potentially Provide Translation In The Future)
            if "accept-language" in self.headers:
                utm_parameters["language"] = self.headers["accept-language"]

            # User Agent - TODO: Figure Out If/How To Anonymize This
            if "user-agent" in self.headers:
                utm_parameters["user_agent"] = self.headers["user-agent"]

            # Cloudflare Forwarded IP
            if 'CF-Connecting-IP' in self.headers:
                ip_address: str = self.headers["CF-Connecting-IP"]
            # NGinx Forwarded IP
            elif 'X-Real-IP' in self.headers:
                ip_address: str = self.headers["X-Real-IP"]
            # Direct IP Connecting To This Server
            else:
                ip_address: str = str(self.client_address[0])

            # Anonymized IP Address
            utm_parameters["ip_address"] = anonymize_ip(ip_address)

            # {'ip': '162.144.105.45', 'country_short': 'US', 'country_long': 'United States of America', 'region': 'Utah', 'city': 'Provo', 'latitude': 40.213909, 'longitude': -111.634071, 'zipcode': '84606', 'timezone': '-07:00'}
            ip_record: IP2Location.IP2LocationRecord = self.ip_lookup.get_all(ip_address)

            # {'is_proxy': 1, 'proxy_type': 'PUB', 'country_short': 'US', 'country_long': 'United States of America', 'region': 'Utah', 'city': 'Provo', 'isp': 'Unified Layer', 'domain': 'unifiedlayer.com', 'usage_type': 'DCH', 'asn': '46606', 'as_name': 'UNIFIEDLAYER-AS-1', 'last_seen': '30'}
            proxy_record: IP2Proxy.IP2ProxyRecord = self.proxy_lookup.get_all(ip_address)

            # Country
            utm_parameters["country"] = ip_record.country_short if ip_record.country_short != "-" else None

            # Region
            utm_parameters["region"] = ip_record.region if ip_record.region != "-" else None

            # City
            utm_parameters["city"] = ip_record.city if ip_record.city != "-" else None

            # Latitude
            utm_parameters["latitude"] = ip_record.latitude if ip_record.latitude != 0 else None

            # Longitude
            utm_parameters["longitude"] = ip_record.longitude if ip_record.longitude != 0 else None

            # ZipCode
            utm_parameters["zipcode"] = ip_record.zipcode if ip_record.zipcode != "-" else None

            # Identify If Proxy
            utm_parameters["is_proxy"] = proxy_record["is_proxy"]

            # https://blog.ip2location.com/knowledge-base/what-are-the-proxy-types-supported-in-ip2proxy/
            # VPN = Hiding IP Address, TOR = Dark Web Anonymity, DCH = Host Provider/Datacenter Anonymity, PUB = Proxy Server, WEB = Web Based Proxy, SES = Spidering/Bots, RES = Proxy Through Residential IP Address
            utm_parameters["proxy_type"] = proxy_record["proxy_type"] if proxy_record["proxy_type"] != "-" else None

            # Insert Into DataFrame
            analytics_df: pd.DataFrame = pd.DataFrame(utm_parameters, index=[0])

            # If Client Doesn't Want To Be Tracked, Do Not Log, Otherwise Log Anonymized Data
            if not ("DNT" in self.headers and self.headers["DNT"] == "1"):
                analytics_df.to_sql('web', con=self.analytics_engine, if_exists='append', index=False)
        except Exception as e:
            self.logger.error(f"UTM Parsing Error: {e}")

    def version_string(self):
        return "Rover"
