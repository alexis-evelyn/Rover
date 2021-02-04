#!/bin/python3
import json
import logging
import pandas as pd

from typing import List, TextIO
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


def save_accounts_to_file(accounts: pd.DataFrame):
    # Drop Blank Columns
    accounts.drop(columns=["president_number", "notes", "end_term"], inplace=True)

    # Drop Non-44 Accounts
    # all_accounts = all_accounts[(all_accounts["twitter_handle"].str.contains("44"))]

    # Drop 44 Accounts
    # all_accounts = all_accounts[~(all_accounts["twitter_handle"].str.contains("44"))]

    # Drop Accounts With 0 Tweets
    # all_accounts = all_accounts[~(all_accounts["total_tweets"] == 0)]

    accounts.to_csv("working/presidential-tweets/import-all.csv", index=False)


def load_accounts_json(file_path: str, president_number: int, notes: str, end_term: str) -> pd.DataFrame:
    records_data: str = "".join(open(file=file_path, mode="r").readlines())
    records: dict = json.loads(records_data)["data"]

    accounts: pd.DataFrame = pd.DataFrame(records)

    rename_columns: dict = {
        "username": "twitter_handle",
        "id": "twitter_user_id",
        "public_metrics": "total_tweets",
        "created_at": "account_creation"
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
        "archived", "suspended", "notes", "first_name", "last_name", "end_term", "party", "account_creation"
    ]

    # Drop Non-Important Columns
    accounts = accounts.reindex(keep_columns, axis=1)

    # I'm sad that I cannot vectorize loading a bunch of json string from a series
    # accounts["total_tweets"] = json.loads(accounts["total_tweets"])["tweet_count"]
    accounts["total_tweets"] = read_total_tweets(accounts["total_tweets"])

    return accounts


def load_existing_entries(file_path: str) -> pd.DataFrame:
    e_dtype: dict = {
        "twitter_user_id": "string"
    }
    accounts: pd.DataFrame = pd.read_csv(filepath_or_buffer=file_path, dtype=e_dtype, keep_default_na=False,
                                         na_values=[' '])
    return accounts


# TODO: Manually Ensure ONDCP45 Is Fixed From ONDCP
def find_wrong_entries(twitter_df: pd.DataFrame, repo_df: pd.DataFrame):
    repo_ids: list[str] = repo_df["twitter_user_id"].to_list()

    # 826093318878670848 Should Be Excluded Since It's Correct
    # 1214584249690607616 Should Be Included Since It's Wrong (Instead Opting For 1214584249690607618 As Its Replacement)
    temp: pd.DataFrame = twitter_df.loc[~(twitter_df["twitter_user_id"].isin(repo_ids))]
    # temp = repo_df.loc[repo_df["twitter_user_id"] == 818925774493405184]

    temp = temp.reindex(["twitter_handle", "twitter_user_id"], axis=1)

    temp.reset_index(inplace=True, drop=True)
    print(temp)
    return temp


def fix_accounts_ids():
    all_accounts: pd.DataFrame = load_accounts_json(file_path="working/presidential-tweets/all-auto-accounts.json",
                                                    president_number=0,
                                                    notes="",
                                                    end_term="")

    existing_accounts: pd.DataFrame = load_existing_entries("working/presidential-tweets/all-accounts-exported.csv")

    fixed_entries: pd.DataFrame = find_wrong_entries(twitter_df=all_accounts, repo_df=existing_accounts)

    merged: pd.DataFrame = existing_accounts.merge(fixed_entries, on="twitter_handle", how="outer")
    merged['twitter_user_id'] = merged['twitter_user_id_y'].where(merged['twitter_user_id_y'].notnull(),
                                                                  merged['twitter_user_id_x'])
    merged.drop(['twitter_user_id_x', 'twitter_user_id_y'], axis=1, inplace=True)

    # merged.drop(columns=["notes", "pronouns", "party", "first_name", "last_name", "end_term", "start_term", "suffix", "middle_name"], inplace=True)
    merged.to_csv("working/presidential-tweets/merged.csv", index=False)

    print(merged)


def add_account_creation_dates():
    all_accounts: pd.DataFrame = load_accounts_json(file_path="working/presidential-tweets/all-accounts.json",
                                                    president_number=0,
                                                    notes="",
                                                    end_term="")
    all_accounts = all_accounts.reindex({"twitter_user_id", "account_creation"}, axis=1)

    # 2017-03-10T16:22:22.000Z ->
    # print("Fixing Dates")  # mm/dd/yyyy -> yyyy-mm-dd
    all_accounts['account_creation'] = all_accounts['account_creation'].str.replace(
        r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}).(\d{3})Z', r'\1-\2-\3 \4:\5:\6', regex=True)

    existing_accounts: pd.DataFrame = load_existing_entries("working/presidential-tweets/all-accounts-exported.csv")

    merged: pd.DataFrame = existing_accounts.merge(all_accounts, on="twitter_user_id", how="outer")
    merged['account_creation'] = merged['account_creation_y'].where(merged['account_creation_y'].notnull(),
                                                                    merged['account_creation_x'])
    merged.drop(['account_creation_x', 'account_creation_y'], axis=1, inplace=True)

    # merged.drop(columns=["notes", "pronouns", "party", "first_name", "last_name", "end_term", "start_term", "suffix",
    #                      "middle_name"], inplace=True)
    merged.to_csv("working/presidential-tweets/account_creation.csv", index=False)

    print(merged)


if __name__ == '__main__':
    add_account_creation_dates()
