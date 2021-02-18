#!/usr/bin/python
import logging
import re
from typing import List
from urllib.parse import urlparse, ParseResult

from archiver.tweet_api_two import TweetAPI2
from rover import config


def send_link(api: TweetAPI2, status: dict):
    logger = logging.getLogger("Link")

    if "entities" in status and "urls" in status["entities"]:
        urls: List[dict] = status["entities"]["urls"]

        new_status = "No link found in the tweet!!! Tweet Metadata Bugged?"
        if len(urls) > 0:
            twitter_url_regex: str = r'https?://twitter.com/[A-Za-z0-9]+/status/[0-9]+'
            url_parsed: ParseResult = urlparse(url=urls[0]['expanded_url'])
            url: str = url_parsed.scheme + "://" + url_parsed.hostname + url_parsed.path
            url: str = url if url[-1] != "/" else url[:-1]

            if re.match(pattern=twitter_url_regex, string=url):
                tweet_id: str = url.split(sep="/")[-1]

                utm_source: str = "twitter"
                utm_medium: str = "rover"
                utm_campaign: str = "link"
                utm_content: str = status["id"]
                new_status = f"If the tweet is archived, you'll find it at {config.SITEMAP_PREFIX}{tweet_id}?utm_source={utm_source}&utm_medium={utm_medium}&utm_campaign={utm_campaign}&utm_content={utm_content}"
            else:
                new_status = f"{url} Is Not A Tweet URL!!!"
    else:
        new_status = "No link found in the tweet!!!"

    if config.REPLY:
        # Make Verbose?
        logger.debug(f"Link Status: {new_status}")

        api.send_tweet(in_reply_to_status_id=status["id"], status=new_status)
