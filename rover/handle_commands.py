#!/usr/bin/python

import logging
import twitter

from doltpy.core.system_helpers import get_logger
from typing import Optional

from archiver.tweet_api_two import TweetAPI2
from rover import commands

logger: logging.Logger = get_logger(__name__)
INFO_QUIET: Optional[int] = None
VERBOSE: Optional[int] = None


def process_command(api: TweetAPI2, status: dict,
                    info_level: int = logging.INFO + 1,
                    verbose_level: int = logging.DEBUG - 1):

    global INFO_QUIET
    INFO_QUIET = info_level

    global VERBOSE
    VERBOSE = verbose_level

    # TODO: Implement Better Command Parsing Handling
    if "search" in status["text"]:
        commands.search_text(api=api, status=status, regex=False)
    elif "regex" in status["text"]:
        commands.search_text(api=api, status=status, regex=True)
    elif "image" in status["text"]:
        commands.draw_image(api=api, status=status)
    elif "hello" in status["text"]:
        commands.say_hello(api=api, status=status)
    elif "analyze" in status["text"]:
        commands.analyze_tweet(api=api, status=status)
    elif "help" in status["text"]:
        commands.give_help(api=api, status=status)
