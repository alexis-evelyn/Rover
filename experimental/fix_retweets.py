#!/bin/python3
import json
import logging
import pandas as pd

from typing import List
from doltpy.core import Dolt, DoltException, system_helpers
from doltpy.etl import get_df_table_writer


def fix_quote(tweet_id: str, data: dict):
    # Extract Tweet Info
    tweet = data['data']
    metadata = data['includes']

    # Detect if Quote Tweet
    isQuote = False
    quotedTweetId = None
    iteration = -1

    # If Has Referenced Tweets Key
    if 'referenced_tweets' in tweet:
        for refTweets in tweet['referenced_tweets']:
            iteration = iteration + 1

            if refTweets['type'] == 'quoted':
                isQuote = True
                quotedTweetId = refTweets['id']
                break

    # Get Retweeted User's ID and Tweet Date
    quotedUserId = None
    quotedTweetDate = None
    quotedTweetText = None

    # Pull From Same Iteration
    if 'tweets' in metadata and isQuote and iteration < len(metadata['tweets']):
        quotedUserId = metadata['tweets'][iteration]['author_id']
        quotedTweetDate = metadata['tweets'][iteration]['created_at']
        quotedTweetText = metadata['tweets'][iteration]['text']

    # if quotedUserId is None:
    #     print(f'ID: {tweet["id"]}')
    #     exit(1)

    # print("Quoted User ID: " + ("Not Set" if quotedUserId is None else quotedUserId))
    # print("Quoted Tweet ID: " + ("Not Set" if quotedTweetId is None else quotedTweetId))
    # print("Quoted Tweet Date: " + ("Not Set" if quotedTweetDate is None else quotedTweetDate))
    # print("Quoted Tweet Text: " + ("Not Set" if quotedTweetText is None else quotedTweetText))

    return {
        "id": tweet_id,
        "isQuote": int(isQuote),
        "quotedUserId": quotedUserId,
        "quotedTweetId": quotedTweetId,
        "quotedTweetDate": quotedTweetDate,
        "quotedTweetText": quotedTweetText
    }


def fix_retweet(tweet_id: str, data: dict):
    # Extract Tweet Info
    tweet = data['data']
    metadata = data['includes']

    # Detect if Retweet
    isRetweet = False
    retweetedTweetId = None
    iteration = -1

    # Get Retweeted User's ID and Tweet Date
    retweetedUserId = None
    retweetedTweetDate = None
    retweetedTweetText = None

    # If Has Referenced Tweets Key
    if 'referenced_tweets' in tweet:
        for refTweets in tweet['referenced_tweets']:
            iteration = iteration + 1

            # Damn, Trump. Always gotta make my work harder. :P - Tweet ID: 685161219624464384
            if refTweets['type'] == 'retweeted':
                isRetweet = True
                retweetedTweetId = refTweets['id']
                break

    # TODO: Implement Fix on Main Script
    # Pull From Same Iteration
    if 'tweets' in metadata and isRetweet:
        for r_tweet in metadata['tweets']:
            if r_tweet["id"] == retweetedTweetId:
                retweetedUserId = r_tweet['author_id']
                retweetedTweetDate = r_tweet['created_at']
                retweetedTweetText = r_tweet['text']
                break

    # print("Retweeted User ID: " + ("Not Set" if retweetedUserId is None else retweetedUserId))
    # print("Retweeted Tweet ID: " + ("Not Set" if retweetedTweetId is None else retweetedTweetId))
    # print("Retweeted Tweet Date: " + ("Not Set" if retweetedTweetDate is None else retweetedTweetDate))
    # print("Retweeted Tweet Text: " + ("Not Set" if retweetedTweetText is None else retweetedTweetText))
    return {
        "id": tweet_id,
        "isRetweet": int(isRetweet),
        "retweetedUserId": retweetedUserId,
        "retweetedTweetId": retweetedTweetId,
        "retweetedTweetDate": retweetedTweetDate,
        "text": retweetedTweetText
    }


def main():
    logging.Logger.setLevel(system_helpers.logger, logging.CRITICAL)

    get_quote_tweets: str = '''
        select * from tweets where json like "%\\"type\\": \\"quoted\\"%";
    '''

    get_retweets: str = '''
        select * from tweets where json like "%\\"type\\": \\"retweeted\\"%";
    '''

    repo: Dolt = Dolt('working/presidential-tweets')

    quote_tweets: dict = repo.sql(query=get_quote_tweets, result_format="csv")

    quote_list: List[dict] = []
    for quote_tweet in quote_tweets:
        try:
            cell: dict = json.loads(quote_tweet["json"])
            quote_dict: dict = fix_quote(tweet_id=quote_tweet["id"], data=cell)
            quote_tweet.update(quote_dict)

            quote_list.append(quote_tweet)
        except:
            print(f"Quote Error: {quote_tweet}")
            exit(1)

    retweets: dict = repo.sql(query=get_retweets, result_format="csv")

    retweet_list: List[dict] = []
    for retweet in retweets:
        try:
            cell: dict = json.loads(retweet["json"])
            retweet_dict: dict = fix_retweet(tweet_id=retweet["id"], data=cell)
            retweet.update(retweet_dict)

            retweet_list.append(retweet)
        except:
            print(f"Retweet Error: {retweet}")
            exit(1)

    quote_pd: pd.DataFrame = pd.DataFrame(quote_list)
    quote_pd['date'] = quote_pd['date'].str.replace(r' +0000 UTC', '', regex=False)
    quote_pd['repliedToTweetDate'] = quote_pd['repliedToTweetDate'].str.replace(r' +0000 UTC', '', regex=False)
    quote_pd['retweetedTweetDate'] = quote_pd['retweetedTweetDate'].str.replace(r' +0000 UTC', '', regex=False)
    quote_pd['quotedTweetDate'] = quote_pd['quotedTweetDate'].str.replace(r' +0000 UTC', '', regex=False)

    print(quote_pd)

    retweet_pd: pd.DataFrame = pd.DataFrame(retweet_list)
    retweet_pd['date'] = retweet_pd['date'].str.replace(r' +0000 UTC', '', regex=False)
    retweet_pd['repliedToTweetDate'] = retweet_pd['repliedToTweetDate'].str.replace(r' +0000 UTC', '', regex=False)
    retweet_pd['retweetedTweetDate'] = retweet_pd['retweetedTweetDate'].str.replace(r' +0000 UTC', '', regex=False)
    retweet_pd['quotedTweetDate'] = retweet_pd['quotedTweetDate'].str.replace(r' +0000 UTC', '', regex=False)

    print(retweet_pd)

    quote_pd.to_csv("working/presidential-tweets/quote.csv", index=False)
    retweet_pd.to_csv("working/presidential-tweets/retweet.csv", index=False)

    # Prepare Data Writer
    # raw_data_writer = get_df_table_writer("tweets", lambda: quote_pd, ["id"])
    #
    # # Write Data To Repo
    # raw_data_writer(repo)

    # Prepare Data Writer
    # raw_data_writer = get_df_table_writer("tweets", lambda: retweet_pd, ["id"])
    #
    # # Write Data To Repo
    # raw_data_writer(repo)

# StartUp Function
main()
