#!/usr/bin/python
import argparse
import json
import logging

import requests
from doltpy.core import system_helpers
from doltpy.core.system_helpers import get_logger

# Stolen From: https://stackoverflow.com/questions/714063/importing-modules-from-parent-folder#comment23054549_11158224
import os
import sys

sys.path.insert(1, os.path.join(sys.path[0], '..'))

from archiver import config

# Setup For Twitter API
from archiver.tweet_api_two import BearerAuth, TweetAPI2

logger: logging.Logger = get_logger(__name__)
parser = argparse.ArgumentParser(description='Arguments For Experimental Streaming')


def main(arguments: argparse.Namespace):
    with open(config.CREDENTIALS_FILE_PATH, "r") as file:
        credentials = json.load(file)

    # To Differentiate Between Development Environment and Production
    if "BEARER_TOKEN_DIS" in credentials:
        bearer_token: str = credentials['BEARER_TOKEN_DIS']
    else:
        bearer_token: str = credentials['BEARER_TOKEN']

    # Token
    token: BearerAuth = BearerAuth(token=bearer_token)
    tweetAPI: TweetAPI2 = TweetAPI2(auth=token)

    r = tweetAPI.stream_tweets()

    # {"title":"ConnectionException","detail":"This stream is currently at the maximum allowed connection limit.","connection_issue":"TooManyConnections","type":"https://api.twitter.com/2/problems/streaming-connection"}
    for line in r.iter_lines():
        # filter out keep-alive new lines
        if line:
            decoded_line = line.decode('utf-8')
            tweet: dict = json.loads(decoded_line)

            if "title" in tweet:
                logger.error("Cannot Stream: {detail}".format(detail=tweet['detail']))
                exit(1)

            if "data" not in tweet:
                logger.warning(f"Unknown Format: {decoded_line}")
                exit(2)

            logger.warning("Tweet {id}: '{text}' - Matched Rules: {rules}".format(id=tweet['data']['id'], text=tweet['data']['text'], rules=string_representation_of_rules(tweet=tweet)))


def string_representation_of_rules(tweet: dict):
    rules: str = ""
    for rule in tweet['matching_rules']:
        rules = rules + rule['tag'] + ", "

    return rules[:-2]


if __name__ == '__main__':
    # This is to get DoltPy's Logger To Shut Up When Running `this_script.py -h`
    # logging.Logger.setLevel(system_helpers.logger, logging.INFO)

    args = parser.parse_args()
    try:
        main(args)
    except KeyboardInterrupt:
        logger.warning("Exiting By User Request...")
        exit(0)
