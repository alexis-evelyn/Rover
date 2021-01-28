#!/usr/bin/python

import twitter

from rover import config


def give_help(api: twitter.Api, status: twitter.models.Status):
    new_status = "@{user} Commands are image, hello, search, regex, analyze (N/A), and help!!! E.g. for search, type {own_name} search your search text here\n\nI'm also working on a website for the bot. It's nowhere near ready right now though. {website}".format(
        name=status.user.name, own_name=config.TWITTER_USER_HANDLE, user=status.user.screen_name, website=config.WEBSITE_ROOT)

    if config.REPLY:
        api.PostUpdate(in_reply_to_status_id=status.id, status=new_status,
                       exclude_reply_user_ids=[config.TWITTER_USER_ID])
