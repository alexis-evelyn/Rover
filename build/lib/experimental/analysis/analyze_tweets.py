#!/usr/bin/python

import csv
import logging
import os
import time
from decimal import Decimal

import sqlalchemy
import pandas as pd

from doltpy.core import Dolt, ServerConfig, system_helpers
from doltpy.core.system_helpers import get_logger
from sqlalchemy import create_engine
from typing import List, Mapping, Optional

from rover import config
from rover.hostility_analysis import HostilityAnalysis

# Logging
logger: logging.Logger = get_logger(__name__)
VERBOSE = logging.DEBUG - 1
logging.addLevelName(VERBOSE, "VERBOSE")

# SQL Config
repo_port: int = 3307
repo_username: str = "root"
repo_host: str = "127.0.0.1"
repo_database: str = "presidential_tweets"


def debug_csv():
    with open("working/attributes-analysis.csv", 'r') as f:
        reader = csv.reader(f)

        line_number: int = 1
        try:
            for row in reader:
                line_number += 1
        except Exception as e:
            print("Error line %d: %s %s" % (line_number, str(type(e)), e))
        finally:
            print(f"Read {line_number} Lines For Debug CSV")


# Stolen From: https://beepscore.com/website/2018/10/12/using-pandas-with-python-decimal.html
# To Store Pandas Column As Decimal
def decimal_from_value(value):
    return Decimal(value)


def import_tweets_from_csv(analyzer: HostilityAnalysis):
    dtype: dict = {
        "average_word_count": "str",
        # "character_count": "int",
        # "hashtag_count": "int",
        # "lowercase_word_count": "int",
        # "numeric_count": "int",  # Number of Numbers in Tweet
        # "stop_words_count": "int",  # Number of Non-Important Words
        # "uppercase_word_count": "int",
        # "word_count": "int",
        "id": "string"
    }

    logger.info("Importing Tweets To DataFrame")
    analytics_df: pd.DataFrame = pd.read_csv(filepath_or_buffer="working/attributes-analysis.csv", engine="python", dtype=dtype)  # , converters={'average_word_count': decimal_from_value})

    logger.info("Replacing Analysis DataFrame With Ours For Pre-Processing")
    analyzer.tweets = analytics_df
    # print(analyzer.tweets)


def get_new_tweets(analyzer: HostilityAnalysis, analytics_engine: sqlalchemy.engine):
    find_not_analyzed_tweets_query = '''
        select id, text from tweets where id not in (select id from analysis);
    '''

    logger.info("Importing Tweets To DataFrame")
    analytics_df: pd.DataFrame = pd.read_sql(sql=find_not_analyzed_tweets_query, con=analytics_engine)

    logger.info("Adding Analysis Attributes To DataFrame")
    total_count: int = len(analytics_df) - 1
    for index, row in analytics_df.iterrows():
        tweet: Mapping = row.to_dict()

        logger.info(f"Adding {index}/{total_count} To DataFrame")
        analyzer.add_tweet_to_process(tweet=tweet)

    # analytics_df["word_count"] = len(analytics_df["tweet"].str.split(" "))
    # analytics_df["character_count"] = len(analytics_df["tweet"].str.split(" "))
    # analytics_df["average_word_count"] = len(analytics_df["tweet"])
    # analytics_df["stop_words_count"] = avg_word(analytics_df["tweet"].str)
    # analytics_df["hashtag_count"] = len([text for text in analytics_df["tweet"].str.split() if text in analyzer.stop_words])
    # analytics_df["numeric_count"] = len([text for text in analytics_df["tweet"].str.split() if text.isdigit()])
    # analytics_df["uppercase_word_count"] = len([text for text in analytics_df["tweet"].str.split() if text.isupper()])
    # analytics_df["lowercase_word_count"] = len([text for text in analytics_df["tweet"].str.split() if text.islower()])

    logger.info("Saving Attributes To CSV For Backup")
    analyzer.tweets.to_csv(path_or_buf="working/attributes-analysis.csv", index=False)
    # analytics_df.to_csv(path_or_buf="working/attributes-analysis.csv", index=False)


def process_tweets(analyzer: HostilityAnalysis):
    logger.info("Pre-Processing Tweets")
    preprocess: pd.DataFrame = analyzer.preprocess_tweets()

    logger.info("Saving Pre-Processed Tweets")
    preprocess.to_csv(path_or_buf="working/preprocess-analysis.csv", index=False)

    logger.info("Processing Tweets")
    results_dict: List[dict] = analyzer.process_tweets()

    logger.info("Saving Results Into A DataFrame")
    results: pd.DataFrame = pd.DataFrame(results_dict)

    logger.info("Saving Results To CSV For Backup")
    results.to_csv(path_or_buf="working/results-analysis.csv", index=False)

    return results, preprocess


def main():
    # Setup SQL Server
    # server_config: ServerConfig = ServerConfig(port=repo_port)
    # repo: Optional[Dolt] = Dolt(repo_dir=config.ANALYTICS_REPO_PATH,
    #                             server_config=server_config)

    # Start SQL Server
    # logger.info("Starting SQL Server")
    # repo.sql_server()
    # time.sleep(3)

    logger.info("Connecting To SQL Server")
    analytics_engine: sqlalchemy.engine = create_engine(
        f"mysql://{repo_username}@{repo_host}:{repo_port}/{repo_database}", echo=False)

    # Instantiate Text Processor
    analyzer: HostilityAnalysis = HostilityAnalysis(logger_param=logger, verbose_level=VERBOSE)

    if os.path.exists(path="working/attributes-analysis.csv"):
        logger.info("Import Tweets From CSV")
        import_tweets_from_csv(analyzer=analyzer)
    else:
        logger.info("Import Tweets From Database")
        get_new_tweets(analyzer=analyzer, analytics_engine=analytics_engine)

    logger.info("Starting Processing Tweets")
    results, preprocess = process_tweets(analyzer=analyzer)

    logger.info("Dropping Text From Pre-Process For Merge To Export To Database")
    preprocess.drop(columns=["text"], inplace=True)

    logger.info("Merging DataFrames For Export To Database")
    merged: pd.DataFrame = pd.merge(results, preprocess, on=['id'], how='outer')

    logger.info("Saving Merged DataFrame To CSV For Backup")
    merged.to_csv(path_or_buf="working/merged-analysis.csv", index=False)

    logger.info("Saving Results To Database")
    merged.to_sql('analysis', con=analytics_engine, if_exists='append', index=False)

    logger.info("Removing All But Final Backup File")
    os.remove("working/attributes-analysis.csv")
    os.remove("working/results-analysis.csv")
    os.remove("working/preprocess-analysis.csv")

    logger.info("Done")


if __name__ == '__main__':
    # Tell Dolt To Shut Up
    # logging.Logger.setLevel(system_helpers.logger, logging.CRITICAL)

    # debug_csv()
    main()
