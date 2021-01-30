#!/usr/bin/python

from archiver.tweet_api_two import TweetAPI2
from rover import config


def give_help(api: TweetAPI2, status: dict):
    new_status = "Commands are image, hello, search, regex, analyze (N/A), and help!!! E.g. for search, type @{own_name} search your search text here\n\nI'm also working on a website for the bot. It's nowhere near ready right now though. {website}".format(
        name=status["author_screen_name"], own_name=config.TWITTER_USER_HANDLE, user=status["author_user_name"], website=config.WEBSITE_ROOT)

    if config.REPLY:
        api.send_tweet(in_reply_to_status_id=status["id"], status=new_status,
                       exclude_reply_user_ids=[config.TWITTER_USER_ID])
