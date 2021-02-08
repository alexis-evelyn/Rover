#!/usr/bin/python

import logging
from typing import Optional, List

from doltpy.core import Dolt
from doltpy.core.system_helpers import logger

from archiver.tweet_api_two import TweetAPI2
from database import database
from rover import config
from rover.search_tweets import SafeDict, get_search_keywords, convert_search_to_query, get_username_by_id


def search_text(api: TweetAPI2, status: dict, regex: bool = False,
                INFO_QUIET: int = logging.INFO + 1,
                VERBOSE: int = logging.DEBUG - 1):
    # Broken For Some Reason
    # select id, text from trump where text COLLATE utf8mb4_unicode_ci like '%sleepy%joe%' order by id desc limit 10;
    # select count(id) from trump where text COLLATE utf8mb4_unicode_ci like '%sleepy%joe%';

    # select id, text from trump where lower(text) COLLATE utf8mb4_unicode_ci like lower('%sleepy%joe%') order by id desc limit 10;
    # select count(id) from trump where lower(text) COLLATE utf8mb4_unicode_ci like lower('%sleepy%joe%');

    # print(status.tweet_mode)

    status_text = status["text"]

    # This Variable Is Useful For Debugging Search Queries And Exploits
    if regex:
        search_word: str = "regex"
    else:
        search_word: str = "search"

    logger.log(level=VERBOSE, msg=f"Search Word: {search_word} - Status Text: {status_text}")
    original_phrase = get_search_keywords(text=status_text, search_word_query=search_word)

    repo: Dolt = Dolt(config.ARCHIVE_TWEETS_REPO_PATH)
    phrase = convert_search_to_query(phrase=original_phrase, regex=regex)

    search_results: List[dict] = database.search_tweets(search_phrase=phrase,
                                                        repo=repo,
                                                        table=config.ARCHIVE_TWEETS_TABLE,
                                                        hide_deleted_tweets=config.HIDE_DELETED_TWEETS,
                                                        only_deleted_tweets=config.ONLY_DELETED_TWEETS,
                                                        regex=regex)

    # # Print Out 10 Found Search Results To Debug Logger
    # loop_count = 0
    # for result in search_results:
    #     logger.debug("Example Tweet For Phrase \"{search_phrase}\": {tweet_id} - {tweet_text}".format(
    #         search_phrase=original_phrase, tweet_id=result["id"], tweet_text=result["text"]))
    #
    #     loop_count += 1
    #     if loop_count >= 10:
    #         break

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
        author = database.retrieveAccountInfo(account_id=search_post_response["twitter_user_id"])[0][
            "twitter_handle"]
        failed_account_lookup: bool = True

    if search_post_response["isDeleted"] == str(0) and not failed_account_lookup:
        url = "https://twitter.com/{screen_name}/status/{status_id}".format(status_id=search_post_response["id"],
                                                                            screen_name=author)
    else:
        if regex:
            campaign: str = "regex"
        else:
            campaign: str = "search"

        url = "{website_root}/tweet/{status_id}/?utm_source={utm_source}&utm_medium={utm_medium}&utm_campaign={utm_campaign}&utm_content={utm_content}" \
            .format(website_root=config.WEBSITE_ROOT,
                    status_id=search_post_response["id"],
                    utm_source="twitter",
                    utm_medium="rover",
                    utm_campaign=campaign,
                    utm_content=status["id"])

    count: int = database.count_tweets(search_phrase=phrase,
                                       account_id=search_post_response["twitter_user_id"],
                                       repo=repo,
                                       table=config.ARCHIVE_TWEETS_TABLE,
                                       hide_deleted_tweets=config.HIDE_DELETED_TWEETS,
                                       only_deleted_tweets=config.ONLY_DELETED_TWEETS,
                                       regex=regex)

    logger.debug("Count For Phrase \"{search_phrase}\": {count}".format(search_phrase=original_phrase, count=count))

    if count == 1:
        word_times = "time"
    else:
        word_times = "times"

    if regex:
        status_context: str = "matches the regex"
    else:
        status_context: str = "has tweeted about"

    new_status = "@{screen_name} {status_context} \"{search_phrase}\" {search_count} {word_times}. The latest example is at {status_link}".format_map(
        SafeDict(
            status_link=url, screen_name=author,
            search_count=count, word_times=word_times, status_context=status_context))

    possibly_truncated_status: str = truncate_if_needed(original_phrase=original_phrase, new_status=new_status)

    # CHARACTER_LIMIT
    if config.REPLY:
        # api.PostUpdates(in_reply_to_status_id=status["id"], status=possibly_truncated_status, continuation='\u2026')
        api.send_tweet(in_reply_to_status_id=status["id"], status=possibly_truncated_status)

    logger.log(INFO_QUIET, "Sending Status: {new_status}".format(new_status=possibly_truncated_status))
    logger.debug("Status Length: {length}".format(length=len(possibly_truncated_status)))


# TODO: Fix Truncation Code
# TODO: https://www.huffpost.com/entry/twitter-character-count_n_2252956
def truncate_if_needed(original_phrase: str, new_status: str) -> str:
    hotfix_truncate_length: int = 29

    truncate_amount = abs(
        (len('\u2026') + len("{search_phrase}") + config.TWITTER_CHARACTER_LIMIT - len(new_status)) - len(
            original_phrase))

    # Don't Put Ellipses If Search Is Not Truncated
    if (len(original_phrase) + len(new_status) + len('\u2026') - len(
            "{search_phrase}")) >= config.TWITTER_CHARACTER_LIMIT:
        return new_status.format(search_phrase=(original_phrase[:(truncate_amount - hotfix_truncate_length)] + '\u2026'))

    return new_status.format(search_phrase=original_phrase)
