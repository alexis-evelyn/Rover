import time
from typing import Optional

import pandas as pd

# Setup Analytics SQL Server
import sqlalchemy
from doltpy.core import ServerConfig, Dolt
from sqlalchemy import create_engine


def load_tweets(con: sqlalchemy.engine) -> pd.DataFrame:
    # select `id`, `conversation_id`, `json` from tweets where `json` like "%conversation_id%" and `conversation_id` is null;
    get_applicable_tweets: str = '''
        -- select `id`, `json` from tweets where `conversation_id` is null and json is not null;
        select *, cast(quoteTweets as char) as quoteTweets1, cast(replies as char) as replies1, cast(repliedToTweetId as char) as repliedToTweetId1, cast(repliedToUserId as char) as repliedToUserId1, cast(retweetedTweetId as char) as retweetedTweetId1, cast(retweetedUserId as char) as retweetedUserId1, 
        cast(quotedTweetId as char) as quotedTweetId1, cast(quotedUserId as char) as quotedUserId1, cast(hasWarning as char) as hasWarning1 
         
        from tweets where `conversation_id` is null and json is not null;
    '''

    df: pd.DataFrame = pd.read_sql(sql=get_applicable_tweets, con=con, index_col='id')

    # Drop Invalid JSON
    df = df.loc[df["json"].str.contains("conversation_id")]

    # Fix Casting Issue
    df.drop(axis=1, columns=['quoteTweets', 'replies', 'repliedToTweetId', 'repliedToUserId', 'retweetedTweetId', 'retweetedUserId', 'quotedTweetId', 'quotedUserId', 'hasWarning'], inplace=True)
    df.rename(columns={'quoteTweets1': 'quoteTweets', 'replies1': 'replies', 'repliedToTweetId1': 'repliedToTweetId', 'repliedToUserId1': 'repliedToUserId', 'retweetedTweetId1': 'retweetedTweetId', 'retweetedUserId1': 'retweetedUserId', 'quotedTweetId1': 'quotedTweetId', 'quotedUserId1': 'quotedUserId', 'hasWarning1': 'hasWarning'}, inplace=True)

    return df


def parse_conversation_ids(tweets: pd.DataFrame) -> pd.DataFrame:
    conversation_id_regex: str = r'(.*)("conversation_id": ")(\d+)(")(.*)'
    conversation_id_group: str = r'\3'

    tweets["conversation_id"] = tweets["json"].str.replace(conversation_id_regex, conversation_id_group, regex=True)
    # tweets: pd.DataFrame = tweets.loc[tweets["conversation_id"].isnull()]

    # print(tweets)
    return tweets


if __name__ == '__main__':
    server_config: ServerConfig = ServerConfig(port=3305)
    repo: Optional[Dolt] = Dolt(repo_dir='./working/presidential-tweets',
                                server_config=server_config)

    # Start Analytics SQL Server
    repo.sql_server()
    time.sleep(1)
    engine: sqlalchemy.engine = create_engine(
        f"mysql://root@127.0.0.1:3305/presidential_tweets",
        echo=False)

    tweets: pd.DataFrame = load_tweets(con=engine)
    tweets: pd.DataFrame = parse_conversation_ids(tweets=tweets)

    # tweets.drop(axis=1, columns=['json'], inplace=True)
    tweets.to_csv("./working/presidential-tweets/convo-ids.csv")
    print(tweets)
