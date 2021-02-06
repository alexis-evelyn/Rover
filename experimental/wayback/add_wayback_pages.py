#!/usr/bin/python

# alter table tweets add column reference longtext;
import os
import re
from re import Match

import sqlalchemy
import pandas as pd

from typing import Optional, List
from doltpy.core import ServerConfig, Dolt
from sqlalchemy import create_engine

# repo_dir: str = "/Users/alexis/Desktop/presidential-tweets"
repo_dir: str = "working/presidential-tweets"

matched_pages_file: str = "working/wayback-matches.csv"
file_list_cache: str = "working/wayback-files.csv"
tweet_list_cache: str = "working/tweet-list.csv"
directory: str = "working/wayback"
filter_name: str = "-archive"
files_regex: str = fr"{directory}/(\w+)/(\d+){filter_name}.html"

# Setup SQL Server
server_config: ServerConfig = ServerConfig(port=9999)
repo: Optional[Dolt] = Dolt(repo_dir=repo_dir,
                            server_config=server_config)

# Start SQL Server
repo.sql_server()
engine: sqlalchemy.engine = create_engine(
    f"mysql://root@127.0.0.1:9999/presidential_tweets",
    echo=False)


def load_url_list() -> pd.DataFrame:
    # https://web.archive.org/web/20201008220730/https://twitter.com/senkamalaharris
    if not os.path.exists(file_list_cache):
        print("Getting File List")
        listOfFiles = list()
        for (dir_path, _, filenames) in os.walk(directory):
            for file in filenames:
                if "-archive" in file:
                    listOfFiles.append(os.path.join(dir_path, file))

        print("Creating URL List")
        pages: pd.DataFrame = pd.DataFrame(listOfFiles)
        pages.rename(columns={0: "file"}, inplace=True)
        pages["account"] = pages["file"].str.replace(files_regex, r"\1", regex=True)
        pages["timestamp"] = pages["file"].str.replace(files_regex, r"\2", regex=True)
        pages["url"] = "https://web.archive.org/web/" + pages["timestamp"] + "/https://twitter.com/" + pages["account"]

        print("Caching URL List")
        pages.to_csv(file_list_cache, index=False)
    else:
        print("Loading URL List")
        pages: pd.DataFrame = pd.read_csv(file_list_cache)

    return pages


def match_tweets_to_pages(pages: pd.DataFrame):
    get_tweets_to_source: str = '''
        select id, reference from tweets where reference is null;
    '''

    # tweet_list_cache
    tweets: pd.DataFrame = pd.read_sql(sql=get_tweets_to_source, con=engine, index_col='id')

    print("Locate Tweet IDs")
    tweet_id_regex: str = r'tweet-id="(\d+)'

    total_pages = len(pages)
    for page in pages.itertuples():
        with open(page.file) as f:
            lines: List[str] = f.readlines()
            contents: str = "\n".join(lines)
            matches: list = re.findall(tweet_id_regex, contents)

            print(f"{page.Index}/{total_pages} - {len(matches)} Tweets Found For Account: {page.account} At Timestamp: {page.timestamp}")
            # print(tweets)
            for match in matches:
                tweets.at[match, 'reference'] = page.url
                # print(tweets.at[match, 'reference'])
        # break

    # TODO: Determine How To Drop Null `reference` Duplicates Regardless Of Order
    tweets = tweets.groupby(tweets.index).first()

    print("Saving To CSV")
    tweets.to_csv(matched_pages_file)

    return tweets


def add_to_database(references: pd.DataFrame):
    # UPDATE tweets SET reference='{reference}' WHERE id='{tweet_id}';
    update_rows_begin: str = "UPDATE tweets SET reference='"
    update_rows_middle: str = "' WHERE id='"
    update_rows_end: str = "';"

    references["query"] = update_rows_begin + references["reference"] + update_rows_middle + references["id"].astype(str) + update_rows_end

    references = references[references["reference"].notnull()]
    references.reset_index(drop=True, inplace=True)

    # print(references)
    # print(f"0: {references['query'][0]}")
    # print(f"100: {references['query'][100]}")

    reference_size: int = len(references)
    for row in references.itertuples():
        try:
            print(f"{row.Index}/{reference_size} - Updating ID: {row.id}")
            engine.execute(row.query)
        except Exception:
            print(f"Failed To Update ID: {row.id}")


def remove_not_added_tweets(references: pd.DataFrame) -> pd.DataFrame:
    get_existing_ids: str = '''
        select id from tweets where reference is null;
    '''

    existing_tweets: pd.DataFrame = pd.read_sql(sql=get_existing_ids, con=engine)
    references = references[references['id'].isin(existing_tweets["id"].to_list())]
    references.reset_index(drop=True, inplace=True)

    # print(references.loc[references["id"] == 142973571537448960])
    # print(references)
    return references


if __name__ == '__main__':
    if not os.path.exists(matched_pages_file):
        print("Starting Process On Creating Wayback CSV!!!")
        wayback_pages: pd.DataFrame = load_url_list()
        matches: pd.DataFrame = match_tweets_to_pages(pages=wayback_pages)
    else:
        matches: pd.DataFrame = pd.read_csv(filepath_or_buffer=matched_pages_file)

    matches = remove_not_added_tweets(references=matches)
    add_to_database(references=matches)

    print("Done")
