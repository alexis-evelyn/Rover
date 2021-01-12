#!/usr/bin/python
import json
from typing import Optional, List

from doltpy.core import Dolt
from mysql.connector import conversion
from pypika import Query, Table, Order
from pypika.functions import Lower, Count
from pypika.queries import QueryBuilder, CreateQueryBuilder, Column
from pypika.terms import Star, CustomFunction


def latest_tweets(repo: Dolt, table: str, max_responses: int = 10, account_id: Optional[int] = None,
                  hide_deleted_tweets: bool = False, only_deleted_tweets: bool = False,
                  last_tweet_id: Optional[int] = None) -> dict:
    tweets: Table = Table(table)
    query: QueryBuilder = Query.from_(tweets) \
        .select(tweets.id, tweets.twitter_user_id, tweets.date,
                tweets.text, tweets.device, tweets.favorites,
                tweets.retweets, tweets.quoteTweets, tweets.replies,
                tweets.isRetweet, tweets.isDeleted, tweets.repliedToTweetId,
                tweets.repliedToUserId, tweets.repliedToTweetDate,
                tweets.retweetedTweetId, tweets.retweetedUserId,
                tweets.retweetedTweetDate, tweets.hasWarning, tweets.warningLabel) \
        .orderby(tweets.id, order=Order.desc) \
        .limit(max_responses)

    if account_id is not None:
        # Show Results For Specific Account
        query: QueryBuilder = query.where(tweets.twitter_user_id, account_id)

    if last_tweet_id is not None:
        query: QueryBuilder = query.where(tweets.id > last_tweet_id)

    if hide_deleted_tweets:
        # Filter Out Deleted Tweets
        query: QueryBuilder = query.where(tweets.isDeleted == 0)
    elif only_deleted_tweets:
        # Only Show Deleted Tweets
        query: QueryBuilder = query.where(tweets.isDeleted == 1)

    # Retrieve Latest Tweets
    return repo.sql(query=query.get_sql(quote_char=None), result_format="json")["rows"]


def search_tweets(search_phrase: str, repo: Dolt, table: str, max_responses: int = 10, account_id: Optional[int] = None,
                  hide_deleted_tweets: bool = False, only_deleted_tweets: bool = False) -> dict:
    tweets: Table = Table(table)
    query: QueryBuilder = Query.from_(tweets) \
        .select(tweets.id, tweets.twitter_user_id, tweets.date,
                tweets.text, tweets.device, tweets.favorites,
                tweets.retweets, tweets.quoteTweets, tweets.replies,
                tweets.isRetweet, tweets.isDeleted, tweets.repliedToTweetId,
                tweets.repliedToUserId, tweets.repliedToTweetDate,
                tweets.retweetedTweetId, tweets.retweetedUserId,
                tweets.retweetedTweetDate, tweets.hasWarning, tweets.warningLabel) \
        .orderby(tweets.id, order=Order.desc) \
        .limit(max_responses) \
        .where(Lower(tweets.text).like(
            search_phrase.lower()
        )  # TODO: lower(text) COLLATE utf8mb4_unicode_ci like lower('{search_phrase}')
    )

    if account_id is not None:
        # Show Results For Specific Account
        query: QueryBuilder = query.where(tweets.twitter_user_id, account_id)

    if hide_deleted_tweets:
        # Filter Out Deleted Tweets
        query: QueryBuilder = query.where(tweets.isDeleted == 0)
    elif only_deleted_tweets:
        # Only Show Deleted Tweets
        query: QueryBuilder = query.where(tweets.isDeleted == 1)

    # Perform Search Query
    # Use Commit https://github.com/dolthub/dolt/commit/6089d7e15d5fe4b02a4dc13630289baee7f937b0 Until JSON Escaping Bug Is Fixed
    return repo.sql(query=query.get_sql(quote_char=None), result_format="json")["rows"]


def count_tweets(search_phrase: str, repo: Dolt, table: str, account_id: Optional[int] = None,
                 hide_deleted_tweets: bool = False, only_deleted_tweets: bool = False) -> int:
    tweets: Table = Table(table)
    query: QueryBuilder = Query.from_(tweets) \
        .select(Count(tweets.id)) \
        .orderby(tweets.id, order=Order.desc) \
        .where(Lower(tweets.text).like(
            search_phrase.lower()
        )  # TODO: lower(text) COLLATE utf8mb4_unicode_ci like lower('{search_phrase}')
    )

    if account_id is not None:
        # Show Results For Specific Account
        query: QueryBuilder = query.where(tweets.twitter_user_id == account_id)

    if hide_deleted_tweets:
        # Filter Out Deleted Tweets
        query: QueryBuilder = query.where(tweets.isDeleted == 0)
    elif only_deleted_tweets:
        # Only Show Deleted Tweets
        query: QueryBuilder = query.where(tweets.isDeleted == 1)

    # Perform Count Query
    count_result = repo.sql(query=query.get_sql(quote_char=None), result_format="json")["rows"]

    # Retrieve Count of Tweets From Search
    for header in count_result[0]:
        return count_result[0][header]

    return -1


def lookupActiveAccounts(repo: Dolt) -> dict:
    government: Table = Table("government")
    query: QueryBuilder = Query.from_(government) \
        .select(government.twitter_user_id, government.twitter_handle, government.first_name, government.last_name) \
        .where(government.archived == 0)

    return repo.sql(query=query.get_sql(quote_char=None), result_format='json')["rows"]


def lookupLatestTweetId(repo: Dolt, table: str, twitter_user_id: str) -> Optional[int]:
    tweets: Table = Table(table)
    query: QueryBuilder = Query.from_(tweets) \
        .select(tweets.id) \
        .where(tweets.twitter_user_id == twitter_user_id) \
        .orderby(tweets.id, order=Order.desc) \
        .limit(1)

    tweet_id = repo.sql(query=query.get_sql(quote_char=None), result_format='json')["rows"]

    if len(tweet_id) < 1 or 'id' not in tweet_id[0]:
        return None

    return tweet_id[0]['id']


def retrieveTweet(repo: Dolt, table: str, tweet_id: str,
                  hide_deleted_tweets: bool = False, only_deleted_tweets: bool = False) -> Optional[dict]:
    tweets: Table = Table(table)
    query: QueryBuilder = Query.from_(tweets) \
        .select(Star()) \
        .where(tweets.id == tweet_id) \
        .limit(1)

    if hide_deleted_tweets:
        # Filter Out Deleted Tweets
        query: QueryBuilder = query.where(tweets.isDeleted == 0)
    elif only_deleted_tweets:
        # Only Show Deleted Tweets
        query: QueryBuilder = query.where(tweets.isDeleted == 1)

    return repo.sql(query=query.get_sql(quote_char=None), result_format='json')["rows"]


def isAlreadyArchived(repo: Dolt, table: str, tweet_id: str,
                      hide_deleted_tweets: bool = False, only_deleted_tweets: bool = False) -> bool:
    result: Optional[dict] = retrieveTweet(repo=repo, table=table, tweet_id=tweet_id,
                                           hide_deleted_tweets=hide_deleted_tweets,
                                           only_deleted_tweets=only_deleted_tweets)

    if len(result) < 1:
        return False

    return True


def retrieveTweetJSON(repo: Dolt, table: str, tweet_id: str) -> Optional[str]:
    tweets: Table = Table(table)
    query: QueryBuilder = Query.from_(tweets) \
        .select(tweets.id, tweets.json) \
        .where(tweets.id == tweet_id) \
        .limit(1)

    result = repo.sql(query=query.get_sql(quote_char=None), result_format='json')["rows"]

    if len(result) < 1:
        return None

    return result[0]


def setDeletedStatus(repo: Dolt, table: str, tweet_id: str, deleted: bool):
    tweets: Table = Table(table)
    query: QueryBuilder = Query.update(tweets) \
        .set(tweets.isDeleted, int(deleted)) \
        .where(tweets.id == tweet_id)

    repo.sql(query=query.get_sql(quote_char=None), result_format='csv')


def updateTweetWithAPIV1(repo: Dolt, table: str, tweet_id: str, data: dict):
    sql_converter: conversion.MySQLConverter = conversion.MySQLConverter()
    escaped_json: str = sql_converter.escape(value=json.dumps(data))

    tweets: Table = Table(table)
    query: QueryBuilder = Query.update(tweets) \
        .set(tweets.json_v1, escaped_json) \
        .where(tweets.id == tweet_id)

    repo.sql(query=query.get_sql(quote_char=None), result_format="csv")


def createTableIfNotExists(repo: Dolt, table: str):
    query: CreateQueryBuilder = Query.create_table(table=table) \
        .columns(
        Column("id", "bigint unsigned", nullable=False),
        Column("twitter_user_id", "bigint unsigned", nullable=False),

        Column("date", "datetime", nullable=False),
        Column("text", "longtext", nullable=False),
        Column("device", "longtext", nullable=False),

        Column("favorites", "bigint unsigned", nullable=False),
        Column("retweets", "bigint unsigned", nullable=False),
        Column("quoteTweets", "bigint unsigned"),
        Column("replies", "bigint unsigned"),

        Column("isRetweet", "tinyint", nullable=False),
        Column("isDeleted", "tinyint", nullable=False),

        Column("repliedToTweetId", "bigint unsigned"),
        Column("repliedToUserId", "bigint unsigned"),
        Column("repliedToTweetDate", "datetime"),

        Column("retweetedTweetId", "bigint unsigned"),
        Column("retweetedUserId", "bigint unsigned"),
        Column("retweetedTweetDate", "datetime"),

        Column("expandedUrls", "longtext"),

        Column("json", "longtext"),
        Column("json_v1", "longtext"),
        Column("notes", "longtext")
    ).primary_key("id")

    # TODO: Figure Out How To Add The Below Parameters
    # --------------------------------------------------------------------------------------------------------------
    # KEY `twitter_user_id_idx` (`twitter_user_id`),
    # CONSTRAINT `twitter_user_id_ref` FOREIGN KEY (`twitter_user_id`) REFERENCES `government` (`twitter_user_id`)
    # --------------------------------------------------------------------------------------------------------------
    # ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    # --------------------------------------------------------------------------------------------------------------

    repo.sql(query=query.get_sql(quote_char=None), result_format="csv")


def retrieveAccountInfo(repo: Dolt, account_id: int) -> dict:
    government: Table = Table("government")
    query: QueryBuilder = Query.from_(government) \
        .select(Star()) \
        .where(government.twitter_user_id == account_id)

    return repo.sql(query=query.get_sql(quote_char=None), result_format='json')["rows"]


def pickRandomOfficials(repo: Dolt, max_results: int = 3) -> dict:
    # select first_name, last_name from government where twitter_user_id
    # is not null group by first_name, last_name order by rand() limit 3
    randFunc: CustomFunction = CustomFunction("rand()")

    government: Table = Table("government")
    query: QueryBuilder = Query.from_(government) \
        .select(government.first_name, government.last_name) \
        .where(government.twitter_user_id.notnull()) \
        .groupby(government.first_name, government.last_name) \
        .orderby(randFunc.name) \
        .limit(max_results)

    print(query.get_sql(quote_char=None))
    return repo.sql(query=query.get_sql(quote_char=None), result_format='json')["rows"]


def retrieveMissingBroadcastInfo(repo: Dolt, table: str) -> dict:
    tweets: Table = Table(table)
    query: QueryBuilder = Query.from_(tweets) \
        .select(tweets.id, tweets.expandedUrls) \
        .where(tweets.expandedUrls.like("https://twitter.com/i/broadcasts/%")) \
        .where(tweets.broadcast_json.isnull())

    return repo.sql(query=query.get_sql(quote_char=None), result_format='json')["rows"]


def setBroadcastJSON(repo: Dolt, table: str, tweet_id: str, data: dict):
    sql_converter: conversion.MySQLConverter = conversion.MySQLConverter()
    escaped_json: str = sql_converter.escape(value=json.dumps(data))

    tweets: Table = Table(table)
    query: QueryBuilder = Query.update(tweets) \
        .set(tweets.broadcast_json, escaped_json) \
        .where(tweets.id == tweet_id)

    repo.sql(query=query.get_sql(quote_char=None), result_format="csv")


def setStreamJSON(repo: Dolt, table: str, tweet_id: str, data: dict):
    sql_converter: conversion.MySQLConverter = conversion.MySQLConverter()
    escaped_json: str = sql_converter.escape(value=json.dumps(data))

    tweets: Table = Table(table)
    query: QueryBuilder = Query.update(tweets) \
        .set(tweets.stream_json, escaped_json) \
        .where(tweets.id == tweet_id)

    repo.sql(query=query.get_sql(quote_char=None), result_format="csv")


def addMediaFiles(repo: Dolt, table: str, tweet_id: str, data: List[str]):
    sql_converter: conversion.MySQLConverter = conversion.MySQLConverter()
    escaped_json: str = sql_converter.escape(value=json.dumps(data))

    media: Table = Table(table)
    query: QueryBuilder = Query.into(media) \
        .insert(tweet_id, escaped_json)

    # query: QueryBuilder = Query.update(media) \
    #     .set(media.file, escaped_json) \
    #     .where(media.id == tweet_id)

    repo.sql(query=query.get_sql(quote_char=None), result_format="csv")


def retrieveMissingBroadcastFiles(repo: Dolt, tweets_table: str, media_table: str) -> dict:
    # select id from tweets where stream_json is not null and id not in (select id from media);
    media: Table = Table(media_table)
    sub_query: QueryBuilder = Query.from_(media) \
        .select(media.id)

    tweets: Table = Table(tweets_table)
    query: QueryBuilder = Query.from_(tweets) \
        .select(tweets.id, tweets.stream_json) \
        .where(tweets.stream_json.notnull()) \
        .where(tweets.id.notin(sub_query))

    return repo.sql(query=query.get_sql(quote_char=None), result_format='json')["rows"]
