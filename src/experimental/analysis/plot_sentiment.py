#!/usr/bin/python
import os
from datetime import datetime, timedelta

import sqlalchemy
import time
import pandas as pd
import matplotlib.pyplot as plt

from typing import Optional
from doltpy.core import ServerConfig, Dolt
from matplotlib import ticker
from sqlalchemy import create_engine

repo_dir: str = "working/presidential-tweets"
points_csv: str = "working/points.csv"

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


def read_tweets(engine: sqlalchemy.engine, start_date: Optional[datetime] = None,
                end_date: Optional[datetime] = None) -> pd.DataFrame:

    if start_date is not None and end_date is not None:
        # 2009-05-01 15:55:17 +0000 UTC
        # YYYY-MM-DD hh:mm:ss

        start_date_str: str = "{year}-{month}-{day} {hour}:{minute}:{second}".format(
            year=str(start_date.year).zfill(4), month=str(start_date.month).zfill(2), day=str(start_date.day).zfill(2),
            hour=str(start_date.hour).zfill(2), minute=str(start_date.minute).zfill(2), second=str(start_date.second).zfill(2))

        end_date_str: str = "{year}-{month}-{day} {hour}:{minute}:{second}".format(
            year=str(end_date.year).zfill(4), month=str(end_date.month).zfill(2), day=str(end_date.day).zfill(2),
            hour=str(end_date.hour).zfill(2), minute=str(end_date.minute).zfill(2), second=str(end_date.second).zfill(2))

        print("Tweets From Range...")
        print(f"Start Date: {start_date_str}")
        print(f"End Date: {end_date_str}")

        read_tweets_sql: str = '''
            select id, twitter_user_id, date, (select twitter_handle from government where government.twitter_user_id=tweets.twitter_user_id) as twitter_handle from tweets where date > "{start_date}" and date < "{end_date}";
        '''.format(start_date=start_date_str, end_date=end_date_str)

        print(f"SQL: `{read_tweets_sql}`")
    else:
        read_tweets_sql: str = '''
            select id, twitter_user_id, date, (select twitter_handle from government where government.twitter_user_id=tweets.twitter_user_id) as twitter_handle from tweets;
        '''

    tweets = pd.read_sql(sql=read_tweets_sql, con=engine, index_col="id")
    dt_index = pd.DatetimeIndex(tweets["date"])
    tweets["day"] = dt_index.day
    tweets["month"] = dt_index.month
    tweets["year"] = dt_index.year
    tweets["dmy"] = dt_index.day.map(str) + "-" + dt_index.month.map(str) + "-" + dt_index.year.map(str)

    # Convert To Date Object
    tweets["dmy"] = pd.to_datetime(tweets['dmy'], format="%d-%m-%Y")

    # Sort By Date Ascending
    tweets.sort_values(by='dmy', ascending=True)

    tweets.drop(columns=["date"], inplace=True)

    return tweets


def read_analysis(engine: sqlalchemy.engine) -> pd.DataFrame:
    read_analysis_sql: str = '''
            select id, polarity, subjectivity from analysis;
        '''

    analysis = pd.read_sql(sql=read_analysis_sql, con=engine, index_col="id")

    return analysis


def get_dataframe(engine: sqlalchemy.engine, start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None) -> pd.DataFrame:
    print("Reading In Tweets")
    tweets = read_tweets(engine=engine, start_date=start_date, end_date=end_date)

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

    averaged: pd.DataFrame = pd.DataFrame(columns=["date", "handle", "polarity", "subjectivity"])
    for handle in handles:
        rows[handle] = []
        dates: list = data.loc[data["twitter_handle"] == handle]["dmy"].unique().tolist()

        for date in dates:
            print(f"Processing {handle} On Date: {date}")
            point: dict = {
                "date": date,
                "handle": handle,
                "polarity": data.loc[(data["twitter_handle"] == handle) & (data["dmy"] == date)]["polarity"].mean(),
                "subjectivity": data.loc[(data["twitter_handle"] == handle) & (data["dmy"] == date)][
                    "subjectivity"].mean()
            }

            rows[handle].append(point)
        averaged = averaged.append(rows[handle])

    print("Saving Processed Data To CSV For Backup!!!")
    averaged.to_csv(points_csv)

    return averaged


def draw_plot(data: pd.DataFrame):
    # https://pandas.pydata.org/docs/getting_started/intro_tutorials/04_plotting.html
    # TODO: Draw Average Polarity With Solid Line (Different Color Per President)
    # TODO: Draw Average Subjectivity With Shaded Line (Different Color Per President)

    # trump = data.loc[(data["handle"] == "realDonaldTrump")]
    biden = data.loc[(data["handle"] == "JoeBiden")]
    # obama = data.loc[(data["handle"] == "POTUS44")]

    fig, ax = plt.subplots()

    print("Plotting Graph")
    # trump.plot.line(x="date", y="polarity", ax=ax, label="Trump's Polarity", ls="dotted", c="darkred")
    # trump.plot.line(x="date", y="subjectivity", ls="--", ax=ax, label="Trump's Subjectivity", c="red")

    biden.plot.line(x="date", y="polarity", ax=ax, label="Biden's Polarity", ls="dotted", c="blue")
    biden.plot.line(x="date", y="subjectivity", ls="--", ax=ax, label="Biden's Subjectivity", c="darkblue")

    # obama.plot.line(x="date", y="polarity", ax=ax, label="Obama's Polarity", ls="dotted", c="green")
    # obama.plot.line(x="date", y="subjectivity", ls="--", ax=ax, label="Obama's Subjectivity", c="darkgreen")

    # Formatting
    plt.title("Avg Polarity/Avg Subjectivity Of Tweets Per Date Per President")
    plt.ylabel("Polarity/Subjectivity")
    plt.xlabel("Date")
    plt.grid()
    plt.tight_layout()

    # Set X-Axis Labels To Be 1 Per Date
    ax.set(xticks=data["date"].unique())
    # ax.set(xticks=pd.date_range(start=data["date"].min(), end=data["date"].max(), periods=30))

    # (pow(2, 16) / 100) -> 65536 && (pow(2, 16) / 100) - 1 -> 55134
    x_length = (pow(2, 16) / 100) - 1  # len(data["date"].unique())*200
    plt.gcf().set_size_inches(x_length, plt.gcf().get_size_inches()[1])

    # Tick Spacing - 'linear', 'log', 'symlog', 'logit', 'function', 'functionlog'
    # plt.xscale("linear")

    # Forces Legend To Top Right
    # plt.legend(bbox_to_anchor=(1, 1), loc=1, borderaxespad=0)

    # Axis Line At Y=0
    plt.axhline(0, color='black')

    # Limits
    plt.ylim([-1, 1])

    # Actual Size
    # plt.axis([data["date"].min(), data["date"].max(), -1, 1])

    # ...
    # ax.xaxis.set_major_locator(ticker.NullLocator())
    # ax.yaxis.set_major_locator(ticker.NullLocator())

    # Set Margins
    plt.margins(0.0, x=None, y=None, tight=True)

    # Rotate Label
    # plt.draw()
    # ax.set_xticklabels(ax.get_xticks(), rotation='vertical')
    ax.xaxis.set_tick_params(rotation=90)

    # Displaying Plot
    plt.ion()
    fig.savefig("working/plot.svg", bbox_inches='tight')
    fig.savefig("working/plot.png", bbox_inches='tight')
    # plt.show(block=True)


if __name__ == "__main__":
    new: bool = True
    clean: bool = False

    # TODO: Convert start_date and end_date to UTC
    # TODO: Fix Data From Scratch (And Saving)
    # TODO: Remove Hardcoding For Plotting Specific Candidate (e.g. trump, biden, obama)
    # TODO: Calculate Analysis For Not Already Analyzed Tweets (In Range)
    # TODO: Fix Starting Analysis Server In Analysis File (Potentially Just Use This Server If Calculating From Here)

    start_date: datetime = datetime.now() - timedelta(days=7)
    end_date: datetime = datetime.now()

    if new or not os.path.exists(points_csv):
        print("Generating Data From Scratch!!!")
        connection = start_server()
        time.sleep(1)
        merged = get_dataframe(engine=connection, start_date=start_date, end_date=end_date)

        if clean:
            print("Removing Unwanted Candidates!!!")
            cleaned = drop_unwanted_candidates(data=merged)
        else:
            cleaned = merged

        averaged = average_points(data=cleaned)
    else:
        print("Reading Data From CSV!!!")
        averaged = pd.read_csv(points_csv, index_col=0, parse_dates=True)

        # Convert To Date Object
        averaged["date"] = pd.to_datetime(averaged['date'], format="%d-%m-%Y")

        # Sort By Date Ascending
        averaged.sort_values(by='date', ascending=True)

    draw_plot(data=averaged)
    print("Done")
