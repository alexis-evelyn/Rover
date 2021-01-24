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

# CORS
ALLOW_CORS: bool = True
CORS_SITES: str = "*"

# HSTS Preload
ENABLE_HSTS: bool = True
HSTS_SETTINGS: str = "max-age=63072000; includeSubDomains; preload"

# Website URL
WEBSITE_ROOT: str = "https://alexisevelyn.me"

# Config
CONFIG_FILE_PATH: str = "config.json"

# Analytics Repo
ANALYTICS_REPO_URL: str = "alexis-evelyn/rover-analytics"
ANALYTICS_REPO_PATH: str = os.path.join(WORKING_DIRECTORY, "analytics")

# Sitemap Variables
SITEMAP_PREFIX: str = "https://alexisevelyn.me/tweet/"

# Other
REPLY: bool = True
AUTHOR_TWITTER_ID: int = 1008066479114383360
AUTHOR_TWITTER_HANDLE: str = "@AlexisEvelyn42"
HIDE_DELETED_TWEETS: bool = False
ONLY_DELETED_TWEETS: bool = False
