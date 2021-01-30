#!/usr/bin/python

import logging
from typing import Optional, List

from doltpy.core import Dolt
from doltpy.core.system_helpers import logger

from archiver.tweet_api_two import TweetAPI2
from database import database
from rover import config
from rover.commands.search import truncate_if_needed
from rover.hostility_analysis import HostilityAnalysis
from rover.search_tweets import get_search_keywords, convert_search_to_query, get_username_by_id, SafeDict

# TODO: Fix https://stackoverflow.com/a/27437149/6828099
# TODO: Determine Whether Or Not To Redesign Function
from rover.server import helper_functions


def analyze_tweet(api: TweetAPI2, status: dict, regex: bool = False,
                  INFO_QUIET: int = logging.INFO + 1,
                  VERBOSE: int = logging.DEBUG - 1):

    status_text = status["text"]

    # This Variable Is Useful For Debugging Search Queries And Exploits
    original_phrase = get_search_keywords(text=status_text, search_word_query='analyze')

    repo: Dolt = Dolt(config.ARCHIVE_TWEETS_REPO_PATH)
    phrase = convert_search_to_query(phrase=original_phrase, regex=regex)

    search_results = database.search_tweets(search_phrase=phrase, repo=repo, table=config.ARCHIVE_TWEETS_TABLE, regex=regex)

    # Check To Make Sure Results Found
    if len(search_results) < 1:
        no_tweets_found_status = "No results found for \"{search_phrase}\""

        possibly_truncated_no_tweets_found_status: str = truncate_if_needed(original_phrase=original_phrase,
                                                                            new_status=no_tweets_found_status)

        if config.REPLY:
            api.send_tweet(in_reply_to_status_id=status["id"], status=possibly_truncated_no_tweets_found_status)

        logger.log(INFO_QUIET,
                   "Sending Status: {new_status}".format(new_status=possibly_truncated_no_tweets_found_status))
        logger.debug("Status Length: {length}".format(length=len(possibly_truncated_no_tweets_found_status)))
        return

    search_post_response = search_results[0]
    failed_account_lookup: bool = False

    # Attempt To Get Latest Account Handle
    author: Optional[str] = get_username_by_id(api=api, author_id=search_post_response["twitter_user_id"])

    if author is None:
        # If Failed (e.g. suspended account), Then Retrieve Stored Handle From Database
        author = database.retrieveAccountInfo(repo=repo, account_id=search_post_response["twitter_user_id"])[0][
            "twitter_handle"]
        failed_account_lookup: bool = True

    if search_post_response["isDeleted"] == str(0) and not failed_account_lookup:
        url = "https://twitter.com/{screen_name}/status/{status_id}".format(status_id=search_post_response["id"],
                                                                            screen_name=author)
    else:
        url = "{website_root}/tweet/{status_id}/?utm_source={utm_source}&utm_medium={utm_medium}&utm_campaign={utm_campaign}&utm_content={utm_content}" \
            .format(website_root=config.WEBSITE_ROOT,
                    status_id=search_post_response["id"],
                    utm_source="twitter",
                    utm_medium="rover",
                    utm_campaign="analysis",
                    utm_content=status["id"])

    analyzed_tweets: List[dict] = helper_functions.analyze_tweets(logger=logger, VERBOSE=VERBOSE, tweets=search_results)

    if len(analyzed_tweets) < 1:
        failed_tweet_analysis = f"Failed to analyze tweet. Please contact {config.AUTHOR_TWITTER_HANDLE} to have {config.AUTHOR_GENDER} fix the issue."
        api.send_tweet(in_reply_to_status_id=status["id"], status=failed_tweet_analysis)
        return

    analyzed_tweet: dict = analyzed_tweets[0]
    new_status = "Analysis For Tweet Sent By @{screen_name}. Polarity: {polarity}, Subjectivity: {subjectivity}. Analyzed Text: \"{search_phrase}\". The latest example is at {status_link}".format_map(
        SafeDict(
            status_link=url, screen_name=author, polarity=analyzed_tweet["polarity"], subjectivity=analyzed_tweet["subjectivity"]
        ))

    possibly_truncated_status: str = truncate_if_needed(original_phrase=analyzed_tweet["processed_text"], new_status=new_status)

    if config.REPLY:
        api.send_tweet(in_reply_to_status_id=status["id"], status=possibly_truncated_status)
