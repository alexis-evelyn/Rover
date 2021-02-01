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
TEMPORARY_IMAGE_FORMAT: str = "PNG"

# Dolt Repo Vars
ARCHIVE_TWEETS_REPO_PATH: str = os.path.join(WORKING_DIRECTORY, "presidential-tweets")
ARCHIVE_TWEETS_TABLE: str = "tweets"

# Config/Working Files
STATUS_FILE_PATH: str = "latest_status.json"
CREDENTIALS_FILE_PATH: str = "credentials.json"

# Twitter Account Info
# TODO: Figure Out How To Automatically Determine This
TWITTER_USER_ID: int = 870156302298873856
TWITTER_USER_HANDLE: str = "DigitalRoverDog"

# CORS
ALLOW_CORS: bool = True
CORS_SITES: str = "*"

# HSTS Preload
ENABLE_HSTS: bool = True
HSTS_SETTINGS: str = "max-age=63072000; includeSubDomains; preload"

# Send Timing Headers
SEND_TIMING_HEADERS: bool = True

# Website URL
WEBSITE_ROOT: str = "https://alexisevelyn.me"

# Config
CONFIG_FILE_PATH: str = "config.json"

# Analytics Repo
ANALYTICS_REPO_URL: str = "alexis-evelyn/rover-analytics"
ANALYTICS_REPO_PATH: str = os.path.join(WORKING_DIRECTORY, "analytics")
ANALYTICS_USERNAME: str = "root"
ANALYTICS_HOST: str = "127.0.0.1"
ANALYTICS_PORT: int = 3307
ANALYTICS_DATABASE: str = "analytics"
ANALYTICS_REPO_USER_URL: str = "https://www.dolthub.com/repositories/alexis-evelyn/rover-analytics/query/master"
ANALYTICS_CONTACT_INFO_TYPE: str = "email"
ANALYTICS_CONTACT_INFO: str = "alexis dot a dot evelyn at gmail dot com"

# IP/Proxy Files
IP_DATABASE: str = os.path.join(WORKING_DIRECTORY, "IP2LOCATION-LITE-DB11.IPV6.BIN/IP2LOCATION-LITE-DB11.IPV6.BIN")
PROXY_DATABASE: str = os.path.join(WORKING_DIRECTORY, "IP2PROXY-LITE-PX10.BIN/IP2PROXY-LITE-PX10.BIN")

# Sitemap Variables
SITEMAP_PREFIX: str = "https://alexisevelyn.me/tweet/"

# Analytics Messages
COOKIE_POPUP_TRACKING: str = 'This site uses cookies to perform analytics as well as determine what bots visit the site. View the <a href="/privacy" style="color:inherit;">Privacy Policy</a> to learn more. By using this site, you agree to this Privacy Policy. You can opt out of future collection by turning the Do Not Track Header on.'
COOKIE_POPUP_NO_TRACKING: str = 'You are already not being tracked because you have the Do Not Tracker header turned on. If you would like to view the privacy policy anyway, go to <a href="/privacy" style="color:inherit;">Privacy Policy</a> to learn more.'

# Other
REPLY: bool = True
AUTHOR_TWITTER_ID: int = 1008066479114383360
AUTHOR_TWITTER_HANDLE: str = "@AlexisEvelyn42"
AUTHOR_GENDER: str = "her"
HIDE_DELETED_TWEETS: bool = False
ONLY_DELETED_TWEETS: bool = False
GITHUB_REPO: str = "https://github.com/alexis-evelyn/Rover"
TWITTER_CHARACTER_LIMIT: int = 280
