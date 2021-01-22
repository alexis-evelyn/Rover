#!/bin/python3
import json
import logging
import pandas as pd

from typing import List
from doltpy.core import Dolt, DoltException, system_helpers
from doltpy.etl import get_df_table_writer


def missing_tweets_json() -> pd.DataFrame:
    failed_tweets_path: str = "./working/presidential-tweets/failed.jsonl"
    failed_tweets_list: List[dict] = []

    failed_tweets_file = open(failed_tweets_path, 'r')
    for line in failed_tweets_file:
        j_line: dict = json.loads(line)
        failed_tweets_list.append(j_line)

    dtype_dict: dict = {
        "id": "string",  # int64 as string to prevent faffing with scientific numbers
        "isDeleted": "int8",  # tinyint based boolean
        "json": "string"  # json in string format
    }
    failed_tweets: pd.DataFrame = pd.DataFrame(failed_tweets_list)

    # print(failed_tweets)
    return failed_tweets


def get_tweet_file(twitter_csv: str) -> pd.DataFrame:
    twitter_csv_parse_dates: List[str] = ['timestamp', 'retweeted_status_timestamp']

    twitter_csv_datatype: dict = {
        "tweet_id": "int64",  # int (should be string)
        "in_reply_to_status_id": "string",  # int
        "in_reply_to_user_id": "string",  # int
        "source": "string",
        "text": "string",
        "retweeted_status_id": "string",  # int
        "retweeted_status_user_id": "string",  # int
        "expanded_urls": "string"
    }

    twitter_csv_columns: dict = {
        "tweet_id": "id",
        "in_reply_to_status_id": "repliedToTweetId",
        "in_reply_to_user_id": "repliedToUserId",
        "timestamp": "date",
        "source": "device",  # TODO: Filter Out HTML
        "text": "text",
        "retweeted_status_id": "retweetedTweetId",
        "retweeted_status_user_id": "retweetedUserId",
        "retweeted_status_timestamp": "retweetedTweetDate",
        "expanded_urls": "expandedUrls"
    }

    twitter_csv_frame: pd.DataFrame = pd.read_csv(filepath_or_buffer=twitter_csv, dtype=twitter_csv_datatype, parse_dates=twitter_csv_parse_dates)
    twitter_csv_frame.rename(inplace=True, columns=twitter_csv_columns)

    # print(twitter_csv_frame)
    return twitter_csv_frame


failed_tweets: pd.DataFrame = missing_tweets_json()
flotus_tweets: pd.DataFrame = get_tweet_file("./working/presidential-tweets/tweet_csv/flotus.csv")
wh_tweets: pd.DataFrame = get_tweet_file("./working/presidential-tweets/tweet_csv/wh.csv")

# 798232312697720832
flotus_tweets["id"] = flotus_tweets[~flotus_tweets["id"].isin(failed_tweets["id"])]
print(flotus_tweets["id"].unique())

for id in flotus_tweets["id"].unique():
    if float.is_integer(id):
        print(f"ID: {int(id)}")
