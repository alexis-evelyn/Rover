#!/usr/bin/python

import json
from typing import Optional

from doltpy.core import Dolt

from rover import config, search_tweets
from database import database

from urllib.parse import urlparse, parse_qs

from rover.server import helper_functions


def handle_schema(self):
    # Determine Reply and Send It
    send_reply(self=self)


def send_headers(self, content_length: int = 0):
    self.send_response(200)
    self.send_header("Content-type", "application/json")

    helper_functions.handle_tracking_cookie(self=self)

    if "Service-Worker-Navigation-Preload" in self.headers:
        self.send_header("Vary", "Service-Worker-Navigation-Preload")

    if config.ALLOW_CORS:
        self.send_header("Access-Control-Allow-Origin", config.CORS_SITES)

    if config.ENABLE_HSTS:
        self.send_header("Strict-Transport-Security", config.HSTS_SETTINGS)

    self.send_header("Content-Length", content_length)

    self.end_headers()


def send_reply(self):
    url: urlparse = urlparse(self.path)
    queries: dict = parse_qs(url.query)

    response_dict: dict = run_function(url=url, queries=queries)

    response: str = json.dumps(response_dict)
    content_length: int = len(response)

    # logger.debug(f"Content Length: {content_length}")

    # Determine Headers To Send and Send Them
    send_headers(self=self, content_length=content_length)

    self.wfile.write(bytes(response, "utf-8"))


def run_function(url: urlparse, queries: dict) -> dict:
    endpoints = {
        '/schema': send_help,
        '/schema/latest': load_latest_tweets,
        '/schema/search': perform_search,
        '/schema/accounts': lookup_account
    }

    func = endpoints.get(url.path.rstrip('/'), invalid_endpoint)
    return func(queries=queries)


def send_help(queries: dict) -> dict:
    """
        Used To Indicate Existing API Endpoints
        :return: JSON Response With URLs
    """
    return {
        "error": "Please Visit The Schema URL Directly",
        "code": 1
    }


def invalid_endpoint(queries: dict) -> dict:
    """
        Used To Indicate Reaching an API Url That Doesn't Exist
        :return: JSON Error Message With Code For Machines To Process
    """
    return {
        "error": "Invalid Endpoint",
        "code": 1
    }
