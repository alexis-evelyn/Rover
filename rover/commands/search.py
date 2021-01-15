#!/usr/bin/python

import logging
import twitter
from doltpy.core import Dolt
from doltpy.core.system_helpers import logger
from twitter import TwitterError

from database import database
from rover import config
from rover.search_tweets import SafeDict, get_search_keywords, convert_search_to_query, get_username_by_id


def search_text(api: twitter.Api, status: twitter.models.Status,
                INFO_QUIET: int = logging.INFO + 1,
                VERBOSE: int = logging.DEBUG - 1):
    # Broken For Some Reason
    # select id, text from trump where text COLLATE utf8mb4_unicode_ci like '%sleepy%joe%' order by id desc limit 10;
    # select count(id) from trump where text COLLATE utf8mb4_unicode_ci like '%sleepy%joe%';

    # select id, text from trump where lower(text) COLLATE utf8mb4_unicode_ci like lower('%sleepy%joe%') order by id desc limit 10;
    # select count(id) from trump where lower(text) COLLATE utf8mb4_unicode_ci like lower('%sleepy%joe%');

    # print(status.tweet_mode)

    if status.tweet_mode == "extended":
        status_text = status.full_text
    else:
        status_text = status.text

    # This Variable Is Useful For Debugging Search Queries And Exploits
    original_phrase = get_search_keywords(text=status_text)

    repo: Dolt = Dolt(config.ARCHIVE_TWEETS_REPO_PATH)
    phrase = convert_search_to_query(phrase=original_phrase)

    search_results: dict = database.search_tweets(search_phrase=phrase,
                                                  repo=repo,
                                                  table=config.ARCHIVE_TWEETS_TABLE,
                                                  hide_deleted_tweets=config.HIDE_DELETED_TWEETS,
                                                  only_deleted_tweets=config.ONLY_DELETED_TWEETS)

    # Print Out 10 Found Search Results To Debug Logger
    loop_count = 0
    for result in search_results:
        logger.debug("Example Tweet For Phrase \"{search_phrase}\": {tweet_id} - {tweet_text}".format(
            search_phrase=original_phrase, tweet_id=result["id"], tweet_text=result["text"]))

        loop_count += 1
        if loop_count >= 10:
            break

    # Check To Make Sure Results Found
    if len(search_results) < 1:
        no_tweets_found_status = "@{user} No results found for \"{search_phrase}\"".format_map(
            SafeDict(user=status.user.screen_name))

        possibly_truncated_no_tweets_found_status: str = truncate_if_needed(original_phrase=original_phrase, new_status=no_tweets_found_status)

        if config.REPLY:
            api.PostUpdate(in_reply_to_status_id=status.id, status=possibly_truncated_no_tweets_found_status)

        logger.log(INFO_QUIET, "Sending Status: {new_status}".format(new_status=possibly_truncated_no_tweets_found_status))
        logger.debug("Status Length: {length}".format(length=len(possibly_truncated_no_tweets_found_status)))
        return

    search_post_response = search_results[0]
    failed_account_lookup: bool = False
    try:
        # Attempt To Get Latest Account Handle
        author = get_username_by_id(api=api, author_id=search_post_response["twitter_user_id"])
    except TwitterError:
        # If Failed (e.g. suspended account), Then Retrieve Stored Handle From Database
        author = database.retrieveAccountInfo(repo=repo, account_id=search_post_response["twitter_user_id"])[0]["twitter_handle"]
        failed_account_lookup: bool = True

    if search_post_response["isDeleted"] == 0 and not failed_account_lookup:
        url = "https://twitter.com/{screen_name}/statuses/{status_id}".format(status_id=search_post_response["id"],
                                                                              screen_name=author)
    else:
        url = "{website_root}/tweet/{status_id}".format(website_root=config.WEBSITE_ROOT,
                                                        status_id=search_post_response["id"])

    count: int = database.count_tweets(search_phrase=phrase,
                                       account_id=search_post_response["twitter_user_id"],
                                       repo=repo,
                                       table=config.ARCHIVE_TWEETS_TABLE,
                                       hide_deleted_tweets=config.HIDE_DELETED_TWEETS,
                                       only_deleted_tweets=config.ONLY_DELETED_TWEETS)

    logger.debug("Count For Phrase \"{search_phrase}\": {count}".format(search_phrase=original_phrase, count=count))

    if count == 1:
        word_times = "time"
    else:
        word_times = "times"

    new_status = "@{user} @{screen_name} has tweeted about \"{search_phrase}\" {search_count} {word_times}. The latest example is at {status_link}".format_map(
        SafeDict(
            user=status.user.screen_name, status_link=url, screen_name=author,
            search_count=count, word_times=word_times))

    possibly_truncated_status: str = truncate_if_needed(original_phrase=original_phrase, new_status=new_status)

    # CHARACTER_LIMIT
    if config.REPLY:
        api.PostUpdates(in_reply_to_status_id=status.id, status=possibly_truncated_status, continuation='\u2026')

    logger.log(INFO_QUIET, "Sending Status: {new_status}".format(new_status=possibly_truncated_status))
    logger.debug("Status Length: {length}".format(length=len(possibly_truncated_status)))


def truncate_if_needed(original_phrase: str, new_status: str) -> str:
    truncate_amount = abs(
        (len('\u2026') + len("{search_phrase}") + twitter.api.CHARACTER_LIMIT - len(new_status)) - len(original_phrase))

    # Don't Put Ellipses If Search Is Not Truncated
    if (len(original_phrase) + len(new_status) + len('\u2026') - len("{search_phrase}")) >= twitter.api.CHARACTER_LIMIT:
        return new_status.format(search_phrase=(original_phrase[:truncate_amount] + '\u2026'))

    return new_status.format(search_phrase=original_phrase)
