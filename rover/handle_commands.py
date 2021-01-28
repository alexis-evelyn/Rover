#!/usr/bin/python

import logging
import twitter

from doltpy.core.system_helpers import get_logger
from typing import Optional
from rover import commands

logger: logging.Logger = get_logger(__name__)
INFO_QUIET: Optional[int] = None
VERBOSE: Optional[int] = None


def process_command(api: twitter.Api, status: twitter.models.Status,
                    info_level: int = logging.INFO + 1,
                    verbose_level: int = logging.DEBUG - 1):

    global INFO_QUIET
    INFO_QUIET = info_level

    global VERBOSE
    VERBOSE = verbose_level

    # TODO: Implement Better Command Parsing Handling
    if "image" in status.full_text:
        commands.draw_image(api=api, status=status)
    elif "hello" in status.full_text:
        commands.say_hello(api=api, status=status)
    elif "search" in status.full_text:
        commands.search_text(api=api, status=status, regex=False)
    elif "regex" in status.full_text:
        commands.search_text(api=api, status=status, regex=True)
    elif "analyze" in status.full_text:
        commands.analyze_tweet(api=api, status=status)
    elif "help" in status.full_text:
        commands.give_help(api=api, status=status)
