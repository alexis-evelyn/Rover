#!/usr/bin/python

import os

# Working Directory
WORKING_DIRECTORY: str = "working"

# Font Vars
FONT_PATH: str = os.path.join(WORKING_DIRECTORY, "firacode/FiraCode-Bold.ttf")
FONT_SIZE: int = 40

# Image Vars
IMAGE_NAME_OFFSET_MULTIPLIER: float = 25.384615384615385
IMAGE_NAME: str = "Digital Rover"

# Temporary Files Vars
TEMPORARY_IMAGE_PATH: str = os.path.join(WORKING_DIRECTORY, "tmp.png")
TEMPORARY_IMAGE_FORMAT: str = "PNG"

# Dolt Repo Vars
ARCHIVE_TWEETS_REPO_PATH: str = os.path.join(WORKING_DIRECTORY, "presidential-tweets")
ARCHIVE_TWEETS_TABLE: str = "tweets"

# Config Files
STATUS_FILE_PATH: str = "latest_status.json"
CREDENTIALS_FILE_PATH: str = "credentials.json"

# Twitter Account Info
# TODO: Figure Out How To Automatically Determine This
TWITTER_USER_ID: int = 870156302298873856
TWITTER_USER_HANDLE: str = "@DigitalRoverDog"

# Other
REPLY: bool = True
AUTHOR_TWITTER_ID: int = 1008066479114383360
AUTHOR_TWITTER_HANDLE: str = "@AlexisEvelyn42"
HIDE_DELETED_TWEETS: bool = False