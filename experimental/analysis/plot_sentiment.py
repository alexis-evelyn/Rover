#!/usr/bin/python

import sqlalchemy
import time
import pandas as pd

from typing import Optional
from doltpy.core import ServerConfig, Dolt
from sqlalchemy import create_engine

repo_dir: str = "working/presidential-tweets"

# Setup SQL Server
server_config: ServerConfig = ServerConfig(port=9999)
repo: Optional[Dolt] = Dolt(repo_dir=repo_dir,
                            server_config=server_config)


# Start SQL Server
def start_server() -> sqlalchemy.engine:
    repo.sql_server()
    engine: sqlalchemy.engine = create_engine(
        f"mysql://root@127.0.0.1:9999/presidential_tweets",
        echo=False)
    return engine


def read_tweets(engine: sqlalchemy.engine) -> pd.DataFrame:
    read_tweets_sql: str = '''
        select id, twitter_user_id, date, (select twitter_handle from government where government.twitter_user_id=tweets.twitter_user_id) as twitter_handle from tweets;
    '''

    tweets = pd.read_sql(sql=read_tweets_sql, con=engine, index_col="id")
    dt_index = pd.DatetimeIndex(tweets["date"])
    tweets["day"] = dt_index.day
    tweets["month"] = dt_index.month
    tweets["year"] = dt_index.year

    tweets.drop(columns=["date"], inplace=True)

    return tweets


def read_analysis(engine: sqlalchemy.engine) -> pd.DataFrame:
    read_analysis_sql: str = '''
            select id, polarity, subjectivity from analysis;
        '''

    analysis = pd.read_sql(sql=read_analysis_sql, con=engine, index_col="id")

    return analysis


def get_dataframe(engine: sqlalchemy.engine) -> pd.DataFrame:
    print("Reading In Tweets")
    tweets = read_tweets(engine=engine)

    print("Reading In Analysis")
    analysis = read_analysis(engine=engine)

    print("Merging")
    # This tosses any rows that don't share the same index on both DataFrames
    merged = pd.merge(tweets, analysis, left_index=True, right_index=True)

    # print("Displaying Preview of DataFrame")
    # print(merged)
    return merged


def drop_unwanted_candidates(data: pd.DataFrame) -> pd.DataFrame:
    # Keep realDonaldTrump (25073877), JoeBiden (939091), and POTUS44 (1536791610)
    print("Keeping Only Desired Candidates")
    keep: list = ["realDonaldTrump", "JoeBiden", "POTUS44"]  # [25073877, 939091, 1536791610] for twitter_user_id
    data = data[data["twitter_handle"].isin(keep)]

    print("Displaying Preview of DataFrame")
    print(data)
    return data


def average_points(data: pd.DataFrame) -> pd.DataFrame:
    # TODO: Average Polarity By Day By Candidate
    # TODO: Average Subjectivity By Day By Candidate
    print("Averaging Points")
    handles: list = data["twitter_handle"].unique().tolist()
    rows: dict = {}

    for handle in handles:
        rows[handle] = data.loc[data["twitter_handle"] == handle]

    for row in rows:
        print("{handle} Polarity: {polarity}".format(handle=row, polarity=rows[row]["polarity"].mean()))
        print("{handle} Subjectivity: {subjectivity}".format(handle=row, subjectivity=rows[row]["subjectivity"].mean()))

    pass


def draw_plot(data: pd.DataFrame):
    # https://pandas.pydata.org/docs/getting_started/intro_tutorials/04_plotting.html
    # TODO: Draw Average Polarity With Solid Line (Different Color Per President)
    # TODO: Draw Average Subjectivity With Shaded Line (Different Color Per President)
    print("Plotting Graph")
    pass


if __name__ == "__main__":
    connection = start_server()
    time.sleep(1)
    merged = get_dataframe(engine=connection)

    cleaned = drop_unwanted_candidates(data=merged)
    averaged = average_points(data=cleaned)
    draw_plot(data=averaged)
    print("Done")
