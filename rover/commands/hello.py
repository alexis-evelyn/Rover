#!/usr/bin/python

import twitter

from archiver.tweet_api_two import TweetAPI2
from rover import config


def say_hello(api: TweetAPI2, status: dict):
    new_status = "@{user} Hello {name}".format(name=status["author_screen_name"], user=status["author_user_name"])

    if config.REPLY:
        api.send_tweet(in_reply_to_status_id=status["id"], status=new_status)
