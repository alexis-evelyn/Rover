#!/usr/bin/python

import json

from doltpy.core import Dolt

from rover import config, search_tweets
from database import database

from urllib.parse import urlparse, parse_qs


def handle_api(self):
    # Repo
    repo: Dolt = Dolt(config.ARCHIVE_TWEETS_REPO_PATH)
    table: str = config.ARCHIVE_TWEETS_TABLE

    # Determine Reply and Send It
    send_reply(self=self, repo=repo, table=table)


def send_headers(self, content_length: int = 0):
    self.send_response(200)
    self.send_header("Content-type", "application/json")

    if config.ALLOW_CORS:
        self.send_header("Access-Control-Allow-Origin", config.CORS_SITES)

    self.send_header("Content-Length", content_length)

    self.end_headers()


def send_reply(self, repo: Dolt, table: str):
    url: urlparse = urlparse(self.path)
    query_bytes: bytes = url.query
    queries: dict = parse_qs(query_bytes)

    original_search_text: str = queries["text"][0] if "text" in queries else ""

    search_phrase: str = search_tweets.convert_search_to_query(phrase=original_search_text)

    search_results: dict = convertIDsToString(
        search_results=database.search_tweets(search_phrase=search_phrase, repo=repo, table=table))
    tweet_count: int = database.count_tweets(search_phrase=search_phrase, repo=repo, table=table)

    response_dict: dict = {
        "query": str(query_bytes),
        "search_text": original_search_text,
        "count": tweet_count,
        "results": search_results
    }

    response: str = json.dumps(response_dict)
    content_length: int = len(response)

    # logger.debug(f"Content Length: {content_length}")

    # Determine Headers To Send and Send Them
    send_headers(self=self, content_length=content_length)

    self.wfile.write(bytes(response, "utf-8"))


def convertIDsToString(search_results: dict):
    for result in search_results:
        result["id"] = str(result["id"])

    return search_results
