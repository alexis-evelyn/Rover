#!/usr/bin/python

from config import config

import os

# Media Vars - TODO: Setup Config Files For Media Vars
MEDIA_TWEETS_TABLE: str = "media"
MEDIA_FILE_LOCATION: str = "/mnt/prez-media/{tweet_id}/"
# MEDIA_FILE_LOCATION: str = "/Users/alexis/IdeaProjects/Rover/working/prez-media/{tweet_id}"

# Config/Working Files
CREDENTIALS_FILE_PATH: str = "credentials.json"
CACHE_FILE_PATH: str = "archiver_tweet_cache.json"

# Failed Tweets File
FAILED_TWEETS_FILE_PATH: str = os.path.join(config.ARCHIVE_TWEETS_REPO_PATH, "failed_to_add_tweets.jsonl")