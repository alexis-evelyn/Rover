#!/usr/bin/python

import csv
import json
import logging
import math
import os
import threading
import time
from json.decoder import JSONDecodeError
from typing import Optional, TextIO, List
from archiver.video_download import VideoDownloader

import pandas as pd
from doltpy.core import Dolt, DoltException
from doltpy.core.system_helpers import get_logger
from doltpy.etl import get_df_table_writer

from archiver import config
from archiver.tweet_api_two import BearerAuth, TweetAPI2
from config import config as main_config
from database import database


class Archiver(threading.Thread):
    def __init__(self, threadID: int, name: str, threadLock: threading.Lock, requested_wait_time: int = 60,
                 commit: bool = True):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name

        self.logger: logging.Logger = get_logger(__name__)
        self.INFO_QUIET: int = main_config.INFO_QUIET
        self.VERBOSE: int = main_config.VERBOSE
        self.repo: Optional[Dolt] = None

        # Thread Lock To Share With Rover
        self.threadLock = threadLock

        # Setup Repo
        self.initRepo(path=config.ARCHIVE_TWEETS_REPO_PATH,
                      create=False,
                      url=config.ARCHIVE_TWEETS_REPO_URL)

        # Setup For Twitter API
        with open(config.CREDENTIALS_FILE_PATH, "r") as file:
            credentials = json.load(file)

        # Token
        token: BearerAuth = BearerAuth(token=credentials['BEARER_TOKEN'])

        # Twitter API V2 and Potential Alt Auth
        if "ALT_BEARER_TOKEN" in credentials:
            alt_token: BearerAuth = BearerAuth(token=credentials['ALT_BEARER_TOKEN'])
            self.twitter_api: TweetAPI2 = TweetAPI2(auth=token, alt_auth=alt_token)
        else:
            self.twitter_api: TweetAPI2 = TweetAPI2(auth=token)

        # Wait Time Remaining
        self.requested_wait_time = requested_wait_time
        self.wait_time: Optional[int] = None

        # Should Commit Data (For Debugging)
        self.commit: bool = commit

        # Media Threads
        self.media_threads: List[int] = []

    def run(self):
        self.logger.log(self.INFO_QUIET, "Starting " + self.name)

        while 1:
            # Get lock to synchronize threads
            self.threadLock.acquire()

            self.download_tweets()

            # Add Livestream Stuff
            # guest_token: str = self.twitter_api.get_guest_token()
            # self.get_broadcast_urls(guest_token=guest_token)
            # self.download_broadcasts()

            # Release Lock
            self.threadLock.release()

            current_wait_time: int = self.requested_wait_time
            if isinstance(self.wait_time, int):
                current_wait_time: int = self.requested_wait_time if self.requested_wait_time > self.wait_time else self.wait_time

            wait_unit: str = "Minute" if current_wait_time == 60 else "Minutes"  # Because I Keep Forgetting What This Is Called, It's Called A Ternary Operator
            self.logger.log(main_config.INFO_QUIET,
                            "Waiting For {time} {unit} Before Checking For New Tweets".format(
                                time=int(current_wait_time / 60),
                                unit=wait_unit))

            time.sleep(current_wait_time)

    def add_broadcast_to_database(self, tweet_id: int, file: str):
        self.logger.debug(f"Adding {file} To Media Table For Tweet {tweet_id}")
        database.addMediaFiles(repo=self.repo, table=config.MEDIA_TWEETS_TABLE, tweet_id=str(tweet_id), data=[file])

    def download_broadcasts(self):
        missing_broadcasts: dict = database.retrieveMissingBroadcastFiles(repo=self.repo,
                                                                          tweets_table=config.ARCHIVE_TWEETS_TABLE,
                                                                          media_table=config.MEDIA_TWEETS_TABLE)

        for broadcast in missing_broadcasts:
            # print(f"{broadcast['id']}, {broadcast['stream_json']}")

            tweet_id: int = int(broadcast["id"])
            video_url: str = json.loads(broadcast['stream_json'])["source"]["noRedirectPlaybackUrl"]
            file_location: str = config.MEDIA_FILE_LOCATION.format(tweet_id=tweet_id)
            self.logger.debug(f"Preparing To Download Video (From Tweet {broadcast['id']}): {video_url}")

            video_downloader: VideoDownloader = VideoDownloader(threadID=int(tweet_id),
                                                                name=f"Livestream Archive {broadcast['id']}",
                                                                video_url=video_url,
                                                                output_directory=file_location,
                                                                callback=self.add_broadcast_to_database,
                                                                tweet_id=tweet_id)
            video_downloader.start()

    def get_broadcast_urls(self, guest_token: str):
        # TODO: Add Proper Error Checking

        broadcasts: dict = database.retrieveMissingBroadcastInfo(repo=self.repo,
                                                                 tweets_table=config.ARCHIVE_TWEETS_TABLE,
                                                                 media_table=config.MEDIA_TWEETS_TABLE)

        for broadcast in broadcasts:
            try:
                broadcast_id = broadcast["expandedUrls"].split('/')[5]
                broadcast_json: dict = json.loads(
                    self.twitter_api.get_broadcast_json(stream_id=broadcast_id, guest_token=guest_token).text)

                database.setBroadcastJSON(repo=self.repo, table=config.MEDIA_TWEETS_TABLE,
                                          tweet_id=broadcast["id"], data=broadcast_json)

                broadcast_meta_json: Optional[dict] = None
                for broadcast_meta in broadcast_json["broadcasts"]:
                    broadcast_meta_json: dict = broadcast_json["broadcasts"][broadcast_meta]
                    break

                if "media_key" in broadcast_meta_json:
                    media_json: dict = json.loads(
                        self.twitter_api.get_stream_json(media_key=broadcast_meta_json["media_key"],
                                                         guest_token=guest_token).text)

                    database.setStreamJSON(repo=self.repo, table=config.ARCHIVE_TWEETS_TABLE,
                                           tweet_id=broadcast["id"], data=media_json)
            except Exception as e:
                self.logger.error(f"STREAM ERROR: {e}")
                continue

    def download_tweets(self):
        self.logger.log(self.INFO_QUIET, "Checking For New Tweets")

        # Get Active Accounts
        active_accounts = database.lookupActiveAccounts(repo=self.repo)

        # Sanitize For Empty Results
        if len(active_accounts) < 1:
            self.logger.error("No Active Accounts!!! Returning From Archiver!!!")
            return

        self.logger.debug(f"Active Accounts: {len(active_accounts)}")

        # TODO: FIX ME
        # Create Table If Not Exists
        # database.createTableIfNotExists(repo=self.repo, table=config.ARCHIVE_TWEETS_TABLE)

        # self.downloadTweetsFromFile(path=os.path.join(config.ARCHIVE_TWEETS_REPO_PATH, 'download-ids.csv'), update_tweets=False, media_api=False)
        # self.updateTweetsIfDeleted(path=os.path.join(config.ARCHIVE_TWEETS_REPO_PATH, 'download-ids.csv'))
        # os.system(f'cd {config.ARCHIVE_TWEETS_REPO_PATH} && dolt sql -q "select id from tweets, media where tweets.json like \\"%media_key%\\" and media.v1_json is null order by id desc;" -r csv > download-ids.csv')
        # return

        for twitter_account in active_accounts:
            self.logger.log(self.INFO_QUIET, "Checking For Tweets From {twitter_account} - @{twitter_handle}".format(
                twitter_account="{first_name} {last_name}".format(first_name=twitter_account["first_name"],
                                                                  last_name=twitter_account["last_name"]),
                twitter_handle=twitter_account["twitter_handle"]))

            # Download Tweets From File and Archive
            self.downloadNewTweets(twitter_user_id=twitter_account["twitter_user_id"])

        # Check Whether Or Not Should Commit Data (Useful For Debugging)
        if not self.commit:
            self.logger.debug("Returning Without Commit Because Commit Disabled By Flags!!!")
            return

        # Commit Changes If Any
        madeCommit = self.commitData(table=config.ARCHIVE_TWEETS_TABLE, message=config.ARCHIVE_TWEETS_COMMIT_MESSAGE)

        # Don't Bother Pushing If Not Commit
        if madeCommit:
            self.pushData(branch=config.ARCHIVE_TWEETS_REPO_BRANCH)

    def downloadNewTweets(self, twitter_user_id: str):
        # Last Tweet ID
        since_id = database.lookupLatestTweetId(repo=self.repo, table=config.ARCHIVE_TWEETS_TABLE,
                                                twitter_user_id=twitter_user_id)

        # Sanitization
        if not isinstance(since_id, int):
            resp = self.twitter_api.lookup_tweets_via_search(user_id=twitter_user_id)
        else:
            resp = self.twitter_api.lookup_tweets_via_search(user_id=twitter_user_id, since_id=since_id)

        tweets = json.loads(resp.text)

        if "data" not in tweets:
            self.logger.log(self.INFO_QUIET, "No New Tweets Found")
            return

        tweetCount = 0
        for tweet in tweets["data"]:
            tweetCount = tweetCount + 1
            self.logger.log(self.INFO_QUIET, "Tweet {}: {}".format(tweet['id'], tweet['text']))

            full_tweet = self.downloadTweet(tweet_id=tweet['id'])

            # If Not A Tweet and Instead, The Rate Limit, Just Return
            if not isinstance(full_tweet, dict):
                return

            try:
                self.addTweetToDatabase(twitter_user_id=twitter_user_id, data=full_tweet)
            except DoltException as e:
                self.logger.error(f"Failed To Add Tweet '{tweet['id']}' To Database!!! Exception: '{e}'")
                tweets_file: TextIO = open(config.FAILED_TWEETS_FILE_PATH, "a+")
                tweets_file.writelines(json.dumps(tweet) + os.linesep)
                tweets_file.close()

        self.logger.log(self.INFO_QUIET, "Tweet Count: {}".format(tweetCount))

    def downloadTweet(self, tweet_id: str, media_api: bool = False) -> Optional[dict]:
        if media_api:
            resp = self.twitter_api.get_tweet_v1(tweet_id=tweet_id)
        else:
            resp = self.twitter_api.get_tweet(tweet_id=tweet_id)

        headers = resp.headers
        rateLimitResetTime = headers['x-rate-limit-reset']

        # Unable To Parse JSON. Chances Are Rate Limit's Been Hit
        try:
            return json.loads(resp.text)
        except JSONDecodeError:
            now = time.time()
            timeLeft = (float(rateLimitResetTime) - now)

            rateLimitMessage = 'Rate Limit Reset Time At {} which is in {} second(s) ({} minute(s))'.format(
                rateLimitResetTime, timeLeft, timeLeft / 60)

            self.wait_time = math.floor(timeLeft + 60)

            self.logger.error(msg='Received A Non-JSON Value. Probably Hit Rate Limit.')
            self.logger.log(main_config.VERBOSE, msg='Non-JSON Message: {message}'.format(message=resp.text))
            self.logger.error(msg=rateLimitMessage)

    def downloadTweetsFromFile(self, path: str, update_tweets: bool = False, media_api: bool = False):
        with open(path, "r") as file:
            csv_reader = csv.reader(file, delimiter=',')
            line_count = -1
            for row in csv_reader:
                if line_count == -1:
                    self.logger.log(self.VERBOSE, f'Column names are {", ".join(row)}')
                    line_count += 1
                else:
                    self.logger.log(self.VERBOSE, f'\t{row[0]}')
                    line_count += 1

                    # Check If Should Be Updating Existing Tweets (Meant To Save Rate Limit For Batch Operations)
                    if database.isAlreadyArchived(repo=self.repo, table=config.ARCHIVE_TWEETS_TABLE,
                                                  tweet_id=row[0]) and not update_tweets:
                        self.logger.log(self.INFO_QUIET, f"Skipping Existing Tweet: {row[0]}")
                        continue

                    tweet: Optional[dict] = self.downloadTweet(tweet_id=row[0], media_api=media_api)

                    # If Not A Tweet and Instead, The Rate Limit, Just Return
                    if not isinstance(tweet, dict):
                        return

                    if update_tweets:
                        self.logger.log(self.INFO_QUIET, f"Updating Existing Tweet: {row[0]}")
                    else:
                        self.logger.log(self.INFO_QUIET, f"Adding New Tweet: {row[0]}")

                    author_id: Optional[str] = tweet["data"]["author_id"] if "data" in tweet else None

                    try:
                        if media_api:
                            database.updateTweetWithAPIV1(repo=self.repo, table=config.MEDIA_TWEETS_TABLE,
                                                          tweet_id=row[0], data=tweet)
                        else:
                            self.addTweetToDatabase(data=tweet, twitter_user_id=author_id)
                    except DoltException as e:
                        self.logger.error(f"Failed To Add Tweet '{row[0]}' To Database!!! Exception: '{e}'")
                        tweets_file: TextIO = open(config.FAILED_TWEETS_FILE_PATH, "a+")
                        tweets_file.writelines(json.dumps(tweet) + os.linesep)
                        tweets_file.close()

            self.logger.log(self.VERBOSE, f'Processed {line_count} lines.')

    def updateTweetsIfDeleted(self, path: str):
        with open(path, "r") as file:
            csv_reader = csv.reader(file, delimiter=',')
            line_count = -1
            for row in csv_reader:
                if line_count == -1:
                    self.logger.log(self.VERBOSE, f'Column names are {", ".join(row)}')
                    line_count += 1
                else:
                    self.logger.log(self.VERBOSE, f'\t{row[0]}')
                    line_count += 1

                    # Don't Waste Rate Limit If Already Marked Deleted
                    if database.isAlreadyArchived(repo=self.repo, table=config.ARCHIVE_TWEETS_TABLE, tweet_id=row[0],
                                                  only_deleted_tweets=True):
                        return

                    tweet = self.downloadTweet(tweet_id=row[0])

                    # If Not A Tweet and Instead, The Rate Limit, Just Return
                    if not isinstance(tweet, dict):
                        return

                    # Update isDeleted Status
                    if 'errors' in tweet and tweet['errors'][0]['parameter'] == 'id':
                        errorMessage = self.archiveErrorMessage(tweet)

                        database.setDeletedStatus(repo=self.repo, table=config.ARCHIVE_TWEETS_TABLE,
                                                  tweet_id=errorMessage['id'], deleted=errorMessage['isDeleted'])

            self.logger.log(self.INFO_QUIET, f'Processed {line_count} lines.')

    def is_inaccessible_tweet(self, data: dict) -> bool:
        # TODO: Figure Out If Non-Deleted Tweet Error Message Can Pass This Check
        if 'errors' in data and data['errors'][0]['parameter'] == 'id':
            return True

        return False

    def handle_error_tweet(self, data: dict):
        errorMessage = self.archiveErrorMessage(data)
        isArchived: bool = database.isAlreadyArchived(repo=self.repo, table=config.ARCHIVE_TWEETS_TABLE,
                                                      tweet_id=errorMessage['id'])

        if not isArchived:
            self.logger.warning("Cannot Insert Tweet {id} Because Of Missing Twitter Account ID Information!!!".format(
                id=errorMessage['id']))
            tweets_file: TextIO = open(config.FAILED_TWEETS_FILE_PATH, "a+")
            tweets_file.writelines(json.dumps(errorMessage) + os.linesep)
            tweets_file.close()
            return

        # TODO: Decide How To Handle New Tweets That Are Deleted
        database.setDeletedStatus(repo=self.repo, table=config.ARCHIVE_TWEETS_TABLE,
                                  tweet_id=errorMessage['id'], deleted=errorMessage['isDeleted'])

    def addTweetToDatabase(self, twitter_user_id: Optional[str], data: dict):
        # Handle Tweets That Contain Errors (Mostly Missing/Private Tweets)
        if self.is_inaccessible_tweet(data=data):
            self.handle_error_tweet(data=data)
            return

        # Tweet Data
        tweet = self.extractTweet(data)

        # Associate Twitter User ID With Tweet
        tweet["twitter_user_id"] = twitter_user_id

        df = self.getDataFrame(tweet)

        # Use `python3 this-script.py --log=VERBOSE` in order to see this output
        self.logger.log(self.VERBOSE, json.dumps(tweet, indent=4))

        self.writeData(dataFrame=df, requiredKeys=['id'])

        # Debug DataFrame
        # debugDataFrame(df)

    def debugDataFrame(self, dataFrame: pd.DataFrame):
        # Setup Print Options
        pd.set_option('display.max_colwidth', None)
        pd.set_option('max_columns', None)

        # Print DataFrame Info
        self.logger.log(self.VERBOSE, "DataFrame: ")
        self.logger.log(self.VERBOSE, dataFrame.head())

    def retrieveData(self, path: str) -> dict:
        # Read JSON From File
        with open(path) as f:
            data = json.load(f)

        # Print JSON For Debugging
        self.logger.log(self.VERBOSE, data)

        return data

    def archiveErrorMessage(self, data: dict) -> dict:
        # for error in data['errors']:

        return {
            # Tweet ID
            'id': int(data['errors'][0]['value']),

            # Mark As Deleted
            'isDeleted': 1,  # Currently hardcoded

            # Raw Json For Future Processing
            'json': data
        }

    def extractTweet(self, data: dict) -> dict:
        # Extract Tweet Info
        tweet = data['data']
        metadata = data['includes']

        # QUOTE TWEET SECTION ----------------------------------------------------------------------

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

        self.logger.debug("Quoted User ID: " + ("Not Set" if quotedUserId is None else quotedUserId))
        self.logger.debug("Quoted Tweet ID: " + ("Not Set" if quotedTweetId is None else quotedTweetId))
        self.logger.debug("Quoted Tweet Date: " + ("Not Set" if quotedTweetDate is None else quotedTweetDate))
        self.logger.debug("Quoted Tweet Text: " + ("Not Set" if quotedTweetText is None else quotedTweetText))

        # RETWEET SECTION ----------------------------------------------------------------------

        # Detect if Retweet
        isRetweet = False
        retweetedTweetId = None
        iteration = -1

        # If Has Referenced Tweets Key
        if 'referenced_tweets' in tweet:
            for refTweets in tweet['referenced_tweets']:
                iteration = iteration + 1

                if refTweets['type'] == 'retweeted':
                    isRetweet = True
                    retweetedTweetId = refTweets['id']
                    break

        # Get Retweeted User's ID and Tweet Date
        retweetedUserId = None
        retweetedTweetDate = None
        retweetedTweetText = None

        # Pull From Same Iteration
        if 'tweets' in metadata and isRetweet and iteration < len(metadata['tweets']):
            retweetedUserId = metadata['tweets'][iteration]['author_id']
            retweetedTweetDate = metadata['tweets'][iteration]['created_at']
            retweetedTweetText = metadata['tweets'][iteration]['text']

        self.logger.debug("Retweeted User ID: " + ("Not Set" if retweetedUserId is None else retweetedUserId))
        self.logger.debug("Retweeted Tweet ID: " + ("Not Set" if retweetedTweetId is None else retweetedTweetId))
        self.logger.debug("Retweeted Tweet Date: " + ("Not Set" if retweetedTweetDate is None else retweetedTweetDate))
        self.logger.debug("Retweeted Tweet Text: " + ("Not Set" if retweetedTweetText is None else retweetedTweetText))

        # REPLY SECTION ----------------------------------------------------------------------

        repliedToTweetId = None
        repliedToUserId = None
        repliedToTweetDate = None
        isReplyTweet = False
        iteration = -1

        # If Has Referenced Tweets Key
        if 'referenced_tweets' in tweet:
            for refTweets in tweet['referenced_tweets']:
                iteration = iteration + 1

                if refTweets['type'] == 'replied_to':
                    isReplyTweet = True
                    repliedToTweetId = refTweets['id']
                    break

        if 'tweets' in metadata and isReplyTweet and iteration < len(metadata['tweets']):
            repliedToUserId = metadata['tweets'][iteration]['author_id']
            repliedToTweetDate = metadata['tweets'][iteration]['created_at']

        self.logger.debug("Replied To User ID: " + ("Not Set" if repliedToUserId is None else repliedToUserId))
        self.logger.debug("Replied To Tweet ID: " + ("Not Set" if repliedToTweetId is None else repliedToTweetId))
        self.logger.debug("Replied To Tweet Date: " + ("Not Set" if repliedToTweetDate is None else repliedToTweetDate))

        # EXPANDED URLS SECTION ----------------------------------------------------------------------

        # Look For Expanded URLs in Tweet
        expandedUrls = None

        if 'entities' in tweet and 'urls' in tweet['entities']:
            expandedUrls = ""  # Set to Blank String

            # Loop Through Expanded URLs
            for url in tweet['entities']['urls']:
                expandedUrls = expandedUrls + url['expanded_url'] + ', '

            # Remove Extra Comma
            expandedUrls = expandedUrls[:-2]

        # FULL TWEET TEXT SECTION ----------------------------------------------------------------------

        # TODO: Implement Full Tweet Text Finding/Storage
        # if 'tweets' in metadata:
        #     text = ""  # Set to Blank String

        #     # Loop Through Referenced Tweets
        #     for tweet in tweet['tweets']:
        #         text = tweet['text']
        #         break

        # FORM DICTIONARY SECTION ----------------------------------------------------------------------

        return {
            'id': tweet['id'],

            # This Tweet's Metadata
            'date': tweet['created_at'],
            'text': tweet['text'] if retweetedTweetText is None else retweetedTweetText,
            'device': tweet['source'],

            # Engagement Statistics
            'favorites': tweet['public_metrics']['like_count'],
            'retweets': tweet['public_metrics']['retweet_count'],
            'quoteTweets': tweet['public_metrics']['quote_count'],
            'replies': tweet['public_metrics']['reply_count'],

            # This Tweet's Booleans
            'isRetweet': int(isRetweet),
            'isQuote': int(isQuote),
            'isDeleted': 0,  # Currently hardcoded

            # Replied Tweet Info
            'repliedToTweetId': repliedToTweetId,
            'repliedToUserId': repliedToUserId,
            'repliedToTweetDate': repliedToTweetDate,

            # Retweet Info
            'retweetedTweetId': retweetedTweetId,
            'retweetedUserId': retweetedUserId,
            'retweetedTweetDate': retweetedTweetDate,

            # Quote Info
            'quotedTweetId': quotedTweetId,
            'quotedUserId': quotedUserId,
            'quotedTweetDate': quotedTweetDate,
            'quotedTweetText': quotedTweetText,

            # Expanded Urls
            'expandedUrls': expandedUrls,

            # Raw Json For Future Processing
            'json': json.dumps(data)
        }

    def getDataFrame(self, tweet: dict) -> pd.DataFrame:
        # Import JSON Into Panda DataFrame
        return pd.DataFrame([tweet])

    def initRepo(self, path: str, create: bool, url: str = None):
        # Prepare Repo For Data
        if create:
            repo = Dolt.init(path)
            repo.remote(add=True, name='origin', url=url)
            self.repo: Dolt = repo

        self.repo: Dolt = Dolt(path)

    def writeData(self, dataFrame: pd.DataFrame, requiredKeys: list):
        # Prepare Data Writer
        raw_data_writer = get_df_table_writer(config.ARCHIVE_TWEETS_TABLE, lambda: dataFrame, requiredKeys)

        # Write Data To Repo
        raw_data_writer(self.repo)

    def commitData(self, table: str, message: str) -> bool:
        # Check to ensure changes need to be added first
        if not self.repo.status().is_clean:
            self.repo.add(table)
            self.repo.commit(message)
            return True
        return False

    def pushData(self, branch: str):
        self.repo.push('origin', branch)
