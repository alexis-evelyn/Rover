#!/usr/bin/python

import pandas as pd

existing_tweets: pd.DataFrame = pd.read_csv("working/missing/trump-existing.csv")
tweets_list: pd.DataFrame = pd.read_csv("working/missing/trump-sorted.csv")

existing: list = existing_tweets["id"].to_list()

temp: pd.DataFrame = tweets_list.loc[~(tweets_list["id"].isin(existing))]
temp.reset_index(drop=True, inplace=True)

temp.to_csv("working/presidential-tweets/trump-download.csv")

print(temp)
