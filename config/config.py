#!/bin/python3

import logging
import os

# Working Directory
WORKING_DIRECTORY: str = "working"

# Dolt Repo Vars
ARCHIVE_TWEETS_REPO_URL: str = "alexis-evelyn/presidential-tweets"
ARCHIVE_TWEETS_REPO_PATH: str = os.path.join(WORKING_DIRECTORY, "presidential-tweets")
ARCHIVE_TWEETS_TABLE: str = "tweets"
ARCHIVE_TWEETS_COMMIT_MESSAGE: str = "Automated Tweet Update"
ARCHIVE_TWEETS_REPO_BRANCH: str = "master"

# SQL Server Vars
ARCHIVE_USERNAME: str = "root"
ARCHIVE_HOST: str = "127.0.0.1"
ARCHIVE_PORT: int = 3307
ARCHIVE_DATABASE: str = "presidential_tweets"

VERBOSE = logging.DEBUG - 1
logging.addLevelName(VERBOSE, "VERBOSE")

INFO_QUIET = logging.INFO + 1
logging.addLevelName(INFO_QUIET, "INFO_QUIET")