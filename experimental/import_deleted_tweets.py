#!/bin/python3

from missing_tweets import get_tweet_file

import json
import logging
import pandas as pd

from typing import List, TextIO
from doltpy.core import Dolt, DoltException, system_helpers
from doltpy.etl import get_df_table_writer


def get_failed_tweets_list() -> pd.DataFrame:
    failed_tweets_path: str = "working/presidential-tweets/failed.jsonl"
    failed_tweets_df: pd.DataFrame = pd.read_json(path_or_buf=failed_tweets_path, lines=True)

    return failed_tweets_df.reindex(["id"], axis=1)


failed_tweets: pd.DataFrame = get_failed_tweets_list()
# failed_tweets: pd.DataFrame = failed_tweets.loc[(failed_tweets["id"] == 771015132298092546)]
# print(failed_tweets)

flotus: pd.DataFrame = get_tweet_file(twitter_csv="./working/presidential-tweets/tweet_csv/flotus.csv")
wh: pd.DataFrame = get_tweet_file(twitter_csv="./working/presidential-tweets/tweet_csv/wh.csv")

flotus: pd.DataFrame = flotus.loc[(flotus["id"].isin(failed_tweets["id"]))]
wh: pd.DataFrame = wh.loc[(wh["id"].isin(failed_tweets["id"]))]

flotus.reset_index(inplace=True, drop=True)
wh.reset_index(inplace=True, drop=True)

# Debug Drop
# debug_drop: List[str] = ["date", "retweetedTweetDate", "retweetedTweetId", "retweetedUserId", "text", "device"]
# flotus.drop(columns=debug_drop, inplace=True)
# wh.drop(columns=debug_drop, inplace=True)

# Debug Keep
# Fix Retweets From Retweet Column To Drop `RT @...` Text At Beginning
# Fix `text`, `device`, `expandedUrls`
# debug_keep: List[str] = ["id", "device"]  # "expandedUrls" ,"text", "retweetedTweetId", "retweetedUserId"]
# flotus = flotus.reindex(debug_keep, axis=1)
# wh = wh.reindex(debug_keep, axis=1)

# Debug Check If Any Non-Retweets (As Of Writing, There Are None, So I'm Not Bothering To Write A Proper Text Column Modification Function)
# flotus = flotus.loc[flotus["retweetedTweetId"].isnull()]
# wh = wh.loc[wh["retweetedTweetId"].isnull()]

# Fix Retweet Text
# flotus['text'] = flotus['text'].str.replace(r'(^RT @\w*:)(.*)', r'\2', regex=True)
# wh['text'] = wh['text'].str.replace(r'(^RT @\w*:)(.*)', r'\2', regex=True)

# Split Urls Via Commas
flotus_eurls: pd.Series = flotus['expandedUrls'].str.split(',')
wh_eurls: pd.Series = wh['expandedUrls'].str.split(',')

# Recombine Urls
flotus_eurls_list: list = []
for eurl in flotus_eurls.to_list():
    if type(eurl) is list:
        flotus_eurls_list.append(", ".join(eurl))
    else:
        flotus_eurls_list.append(eurl)

wh_eurls_list: list = []
for eurl in wh_eurls.to_list():
    if type(eurl) is list:
        wh_eurls_list.append(", ".join(eurl))
    else:
        wh_eurls_list.append(eurl)

flotus['expandedUrls'] = flotus_eurls_list
wh['expandedUrls'] = wh_eurls_list

# Fix Devices
flotus['device'] = flotus['device'].str.replace(r'^(.*>)(.*)(<\/a>)', r'\2', regex=True)
wh['device'] = wh['device'].str.replace(r'^(.*>)(.*)(<\/a>)', r'\2', regex=True)

# Fix Columns For Import
flotus["twitter_user_id"] = 1093090866
flotus["isRetweet"] = 1
flotus["isDeleted"] = 1
flotus["favorites"] = 0
flotus["retweets"] = 0
flotus["quoteTweets"] = 0
flotus["replies"] = 0

wh["twitter_user_id"] = 30313925
wh["isRetweet"] = 1
wh["isDeleted"] = 1
wh["favorites"] = 0
wh["retweets"] = 0
wh["quoteTweets"] = 0
wh["replies"] = 0

print(flotus)
print(wh)

flotus.to_csv("working/presidential-tweets/import-missing-flotus.csv", date_format='%Y-%m-%d %H:%M:%S', index=False)  # yyyy-mm-dd hh:mm:ss
wh.to_csv("working/presidential-tweets/import-missing-wh.csv", date_format='%Y-%m-%d %H:%M:%S', index=False)  # yyyy-mm-dd hh:mm:ss
