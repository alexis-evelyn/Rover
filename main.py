#!/usr/bin/python

import argparse
import logging
import threading

# Custom Log Levels
import sqlalchemy
from doltpy.core import system_helpers, Dolt, ServerConfig
from doltpy.core.system_helpers import get_logger
from sqlalchemy import create_engine

from config import config
from rover import Rover
from archiver import Archiver

# Dolt Logger - logging.getLogger(__name__)
from rover.server import WebServer

logger: logging.Logger = get_logger(__name__)

# Argument Parser Setup
parser = argparse.ArgumentParser(description='Arguments For Tweet Searcher')
parser.add_argument("-log", "--log", help="Set Log Level (Defaults to INFO_QUIET)",
                    dest='logLevel',
                    default='INFO_QUIET',
                    type=str.upper,
                    choices=['VERBOSE', 'DEBUG', 'INFO', 'INFO_QUIET', 'WARNING', 'ERROR', 'CRITICAL'])

parser.add_argument("-wait", "--wait", help="Set Delay Before Checking For New Tweets In Minutes (Defaults To 1 Minute)",
                    dest='wait',
                    default=1,
                    type=int)

parser.add_argument("-reply", "--reply", help="Reply to Tweets (Useful For Debugging) (Defaults To True)",
                    dest='reply',
                    default=True,
                    type=bool,
                    action=argparse.BooleanOptionalAction)

parser.add_argument("-rover", "--rover", help="Look For Tweets To Respond To (Useful For Disabling Rover Entirely) (Defaults To True)",
                    dest='rover',
                    default=True,
                    type=bool,
                    action=argparse.BooleanOptionalAction)

parser.add_argument("-archive", "--archive", help="Archives Tweets (Useful For Debugging) (Defaults To True)",
                    dest='archive',
                    default=True,
                    type=bool,
                    action=argparse.BooleanOptionalAction)

parser.add_argument("-archive-from-file", "--archive-from-file", help="Only Archive Tweets From File (Useful For Batch Import) (Defaults To False)",
                    dest='archive_from_file',
                    default=False,
                    type=bool,
                    action=argparse.BooleanOptionalAction)

parser.add_argument("-server", "--server", help="Run Webserver (Defaults To True)",
                    dest='server',
                    default=True,
                    type=bool,
                    action=argparse.BooleanOptionalAction)

parser.add_argument("-commit", "--commit", help="Commit Tweets To Repo When Archived (Useful For Debugging) (Defaults To True)",
                    dest='commit',
                    default=True,
                    type=bool,
                    action=argparse.BooleanOptionalAction)

# TODO: Verify Using Lock Correctly - Appears To Be Correct So Far With Testing
threadLock: threading.Lock = threading.Lock()


def main(arguments: argparse.Namespace):
    # Set Logging Level
    logging.Logger.setLevel(system_helpers.logger, arguments.logLevel)  # DoltPy's Log Level
    logger.setLevel(arguments.logLevel)  # This Script's Log Level

    server_config: ServerConfig = ServerConfig(port=config.ARCHIVE_PORT)
    repo: Dolt = initRepo(path=config.ARCHIVE_TWEETS_REPO_PATH,
                          create=False,
                          url=config.ARCHIVE_TWEETS_REPO_URL,
                          server_config=server_config)

    repo.sql_server()
    engine: sqlalchemy.engine = create_engine(
        f"mysql://{config.ARCHIVE_USERNAME}@{config.ARCHIVE_HOST}:{config.ARCHIVE_PORT}/{config.ARCHIVE_DATABASE}",
        echo=False)

    rover: Rover = Rover(threadID=1, name="Rover", requested_wait_time=arguments.wait * 60, reply=arguments.reply, threadLock=threadLock, archive_engine=engine)
    archiver: Archiver = Archiver(threadID=2, name="Archiver", requested_wait_time=arguments.wait * 60, commit=arguments.commit, from_file=arguments.archive_from_file, threadLock=threadLock, archive_engine=engine)
    server: WebServer = WebServer(threadID=3, name="Analysis Server", archive_engine=engine)  # https://www.tutorialspoint.com/python3/python_multithreading.htm

    # Start Archiver
    if arguments.archive:
        archiver.start()

    # Start Rover
    if arguments.rover:
        rover.start()

    # Start Webserver
    if arguments.server:
        server.start()


def initRepo(path: str, create: bool, url: str = None, server_config: ServerConfig = ServerConfig()) -> Dolt:
    # Prepare Repo For Data
    if create:
        repo: Dolt = Dolt.init(path, server_config=server_config)
        repo.remote(add=True, name='origin', url=url)
        return repo

    return Dolt(path, server_config=server_config)


if __name__ == '__main__':
    # This is to get DoltPy's Logger To Shut Up When Running `this_script.py -h`
    logging.Logger.setLevel(system_helpers.logger, logging.CRITICAL)

    args = parser.parse_args()
    try:
        main(args)
    except KeyboardInterrupt:
        logger.warning("Exiting By User Request...")
        exit(0)
