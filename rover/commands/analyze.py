#!/usr/bin/python

import logging

from doltpy.core import Dolt
from doltpy.core.system_helpers import logger

from archiver.tweet_api_two import TweetAPI2
from database import database
from rover import config
from rover.hostility_analysis import HostilityAnalysis
from rover.search_tweets import get_search_keywords, convert_search_to_query


# TODO: Determine Whether Or Not To Redesign Function
def analyze_tweet(api: TweetAPI2, status: dict, regex: bool = False,
                  INFO_QUIET: int = logging.INFO + 1,
                  VERBOSE: int = logging.DEBUG - 1):

    status_text = "12:00 A.M. on the Great Election Fraud of 2020!"  # status.full_text

    # This Variable Is Useful For Debugging Search Queries And Exploits
    original_phrase = get_search_keywords(text=status_text, search_word_query='analyze')

    repo: Dolt = Dolt(config.ARCHIVE_TWEETS_REPO_PATH)
    phrase = convert_search_to_query(phrase=original_phrase, regex=regex)

    search_results = database.search_tweets(search_phrase=phrase, repo=repo, table=config.ARCHIVE_TWEETS_TABLE, regex=regex)

    # Instantiate Text Processor
    analyzer: HostilityAnalysis = HostilityAnalysis(logger_param=logger, verbose_level=VERBOSE)

    # Load Tweets To Analyze
    for result in search_results:
        logger.log(VERBOSE, "Adding Tweet For Processing: {tweet_id} - {tweet_text}".format(tweet_id=result["id"],
                                                                                            tweet_text=result["text"]))
        analyzer.add_tweet_to_process(result)

    analyzer.preprocess_tweets()
    analyzer.process_tweets()
