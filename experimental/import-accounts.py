#!/bin/python3
import json
import logging
import pandas as pd

from typing import List
from doltpy.core import Dolt, DoltException, system_helpers
from doltpy.etl import get_df_table_writer


def load_trump() -> pd.DataFrame:
    # https://twitter.com/search?q=%22This%20is%20an%20archive%20of%20a%20Trump%20Administration%20account%2C%20maintained%20by%20the%20National%20Archives%20and%20Records%20Administration.%22&src=typed_query&f=user
    trump_accounts_path: str = "working/presidential-tweets/trump-accounts.txt"
    trump_accounts: pd.DataFrame = pd.read_csv(trump_accounts_path)

    # handles: str = ""
    # for handle in trump_accounts["twitter_handle"].unique():
    #     handles += handle + ","

    # print(trump_accounts)
    # print(handles)
    return trump_accounts


def read_total_tweets(public_metrics: pd.Series) -> pd.Series:
    tweet_count: List[int] = []
    for index, value in public_metrics.items():
        # print(value["tweet_count"])
        tweet_count.append(value["tweet_count"])

    return pd.Series(name="total_tweets", data=tweet_count)


def load_accounts_json(file_path: str, president_number: int, notes: str, end_term: str) -> pd.DataFrame:
    accounts: pd.DataFrame = pd.read_json(file_path)

    rename_columns: dict = {
        "username": "twitter_handle",
        "id": "twitter_user_id",
        "public_metrics": "total_tweets"
    }

    # Rename Columns From JSON
    accounts.rename(columns=rename_columns, inplace=True)

    row_data: dict = {
        # Hardcoded Values
        "president_number": president_number,
        "archived": 1,
        "suspended": 0,
        "notes": notes,

        # Manually Add and Verify
        "first_name": "N/A",
        "last_name": "N/A",
        "end_term": end_term,
        "party": "N/A",
    }

    # Add Missing Columns
    for key in row_data:
        accounts[key] = row_data[key]

    keep_columns: List[str] = [
        "twitter_handle", "twitter_user_id", "total_tweets", "president_number",
        "archived", "suspended", "notes", "first_name", "last_name", "end_term", "party"
    ]

    # Drop Non-Important Columns
    accounts = accounts.reindex(keep_columns, axis=1)

    # I'm sad that I cannot vectorize loading a bunch of json string from a series
    # accounts["total_tweets"] = json.loads(accounts["total_tweets"])["tweet_count"]
    accounts["total_tweets"] = read_total_tweets(accounts["total_tweets"])

    return accounts


trump_accounts: pd.DataFrame = load_accounts_json(file_path="working/presidential-tweets/trump-accounts.json",
                                                  president_number=45,
                                                  notes="Automatically Added - Trump Presidency",
                                                  end_term="2021-01-20 00:00:00")

all_accounts: pd.DataFrame = load_accounts_json(file_path="working/presidential-tweets/all-accounts.json",
                                                president_number=44,
                                                notes="Automatically Added - Obama Presidency",
                                                end_term="2017-01-20 00:00:00")

# Drop Non-45 Accounts
# trump_accounts = trump_accounts[(trump_accounts["twitter_handle"].str.contains("45"))]

# Drop 45 Accounts
trump_accounts = trump_accounts[~(trump_accounts["twitter_handle"].str.contains("45"))]

# Drop Accounts With 0 Tweets
trump_accounts = trump_accounts[~(trump_accounts["total_tweets"] == 0)]

# Drop Non-44 Accounts
# all_accounts = all_accounts[(all_accounts["twitter_handle"].str.contains("44"))]

# Drop 44 Accounts
all_accounts = all_accounts[~(all_accounts["twitter_handle"].str.contains("44"))]

# Drop Accounts With 0 Tweets
all_accounts = all_accounts[~(all_accounts["total_tweets"] == 0)]

trump_accounts.to_csv("working/presidential-tweets/import-trump.csv", index=False)
all_accounts.to_csv("working/presidential-tweets/import-all.csv", index=False)

# insert_sql_file = open("working/presidential-tweets/insert-trump.sql", mode="w")
# columns: str = ",".join(trump_accounts.columns)
# for row in trump_accounts.itertuples():
#     cell_data: str = ""
#     for cell in range(1, len(trump_accounts.columns) + 1):
#         cell_data += "'" + str(row[cell]) + "',"
#
#     cell_data = cell_data[:-1]
#
#     insert_query = f'''
#         insert into government ({columns}) values ({cell_data});
#     '''
#
#     insert_sql_file.writelines(insert_query)
#     print(insert_query)
# insert_sql_file.close()

# repo: Dolt = Dolt("working/presidential-tweets")
#
# # Prepare Data Writer
# raw_data_writer = get_df_table_writer("government", lambda: trump_accounts, [])
#
# # Write Data To Repo
# raw_data_writer(repo)

print(trump_accounts)
print(all_accounts)
