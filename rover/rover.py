#!/usr/bin/python

import json
import logging
import threading
import time
from typing import Optional, Any, Reversible, List, Tuple
from json.decoder import JSONDecodeError
from os import path

from doltpy.core import DoltException
from doltpy.core.system_helpers import get_logger
from requests import Response
from requests_oauthlib import OAuth1

from archiver.tweet_api_two import TweetAPI2, BearerAuth
from rover import handle_commands, config
from config import config as main_config


class Rover(threading.Thread):
    def __init__(self, threadID: int, name: str, threadLock: threading.Lock, requested_wait_time: int = 60,
                 reply: bool = True):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name

        self.logger: logging.Logger = get_logger(__name__)
        self.INFO_QUIET: int = main_config.INFO_QUIET
        self.VERBOSE: int = main_config.VERBOSE
        self.status_file: str = config.STATUS_FILE_PATH
        self.credentials_file: str = config.CREDENTIALS_FILE_PATH

        # Thread Lock To Share With Archiver
        self.threadLock = threadLock

        # Wait Time Remaining
        self.requested_wait_time = requested_wait_time
        self.wait_time: Optional[int] = None

        # For Debugging
        config.REPLY = reply

        # Debugging Paths
        self.logger.info("Working Directory: {working_directory}".format(working_directory=config.WORKING_DIRECTORY))

        # Setup For Twitter API
        with open(self.credentials_file, "r") as file:
            self.__credentials: dict = json.load(file)
            self.__oauth: OAuth1 = OAuth1(client_key=self.__credentials['consumer']['key'],
                                          client_secret=self.__credentials['consumer']['secret'],
                                          resource_owner_key=self.__credentials['token']['key'],
                                          resource_owner_secret=self.__credentials['token']['secret'])

            # TODO: Add Means To Obtain Tokens Without Manually Going Through The API - https://requests-oauthlib.readthedocs.io/en/latest/oauth1_workflow.html
            # Authentication Method For Accounts
            self.api: TweetAPI2 = TweetAPI2(auth=BearerAuth(token=self.__credentials["BEARER_TOKEN"]), reply_auth=self.__oauth)

        # Get Own Account ID and Handle
        id_handle: Optional[Tuple[str, str]] = self.api.get_account_info()

        # If Failed ID and Handle Retrieval Return
        if id_handle is None:
            self.logger.log(self.INFO_QUIET, f"Failed Logging In On Rover Application!!! Returning!!!")
            return

        # If Successful, Then Set Variables
        config.TWITTER_USER_ID, config.TWITTER_USER_HANDLE = id_handle

        self.user_id: int = int(config.TWITTER_USER_ID)
        self.user_name: str = config.TWITTER_USER_HANDLE

        self.logger.log(self.INFO_QUIET, f"Logged In As @{self.user_name} ({self.user_id})!!!")

    def run(self):
        # Enforce Exiting Rover If ID Handle Lookup Failed
        if not hasattr(self, 'user_id') or not hasattr(self, 'user_name'):
            return

        self.logger.log(self.INFO_QUIET, "Starting " + self.name)

        while 1:
            # Get lock to synchronize threads
            self.threadLock.acquire()

            # Look For Tweets To Respond To
            self.look_for_tweets()

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

    def look_for_tweets(self):
        # self.save_status_to_file(status_id=1335821481557831679)  # For Debugging Bot

        self.logger.log(self.INFO_QUIET, "Checking For New Tweets")
        last_replied_status = self.read_status_from_file()
        replied_to_status = self.process_tweet(latest_status=last_replied_status)

        # if replied_to_status is not None:
        #     self.save_status_to_file(replied_to_status)

    def process_tweet(self, latest_status: int = None) -> Optional[int]:
        mentions_response: Response = self.api.get_mentions(screen_name=config.TWITTER_USER_HANDLE, since_id=latest_status)

        try:
            mentions_dict: dict = json.loads(mentions_response.text)
        except:
            self.logger.error("Could Not Load JSON From Mentions Response!!!")
            return

        if "data" not in mentions_dict:
            self.logger.log(self.VERBOSE, "Data Key Missing From Mentions Response!!!")
            return

        if "includes" not in mentions_dict:
            self.logger.log(self.VERBOSE, "Includes Key Missing From Mentions Response!!!")
            return

        mentions: List[dict] = mentions_dict["data"]
        meta: dict = mentions_dict["includes"]
        tweet_includes: Optional[List[dict]] = meta["tweets"] if "tweets" in meta else None

        latest_status = None
        for mention in reversed(mentions):
            # Don't Respond To Own Tweets (870156302298873856 is user id for @DigitalRoverDog)
            if str(mention["author_id"]) == str(self.user_id):
                continue

            # To Prevent Implicit Replying (So the bot only replies to explicit requests)
            if tweet_includes is not None:
                included_tweet: Optional[dict] = next((item for item in tweet_includes if "id" in item and item["id"] == mention["id"]), None)
            else:
                included_tweet = None

            if not self.is_explicitly_mentioned(mention=mention, included_tweet=included_tweet):
                self.logger.log(self.VERBOSE, f"Not Explicitly Mentioned Data: {mention}")
                continue

            if "includes" in mentions_dict and "users" in mentions_dict["includes"]:
                users: List[dict] = mentions_dict["includes"]["users"]

                for user in users:
                    if user["id"] == mention["author_id"]:
                        mention["author_screen_name"] = user["name"]
                        mention["author_user_name"] = user["username"]
                        break

            self.logger.log(self.INFO_QUIET,
                            "Responding To Tweet From @{user}: {text}".format(user=mention["author_user_name"],
                                                                              text=mention["text"]))

            try:
                handle_commands.process_command(api=self.api, status=mention,
                                                info_level=self.INFO_QUIET,
                                                verbose_level=self.VERBOSE)
            except DoltException as e:
                self.logger.error(
                    f"Failed To Process SQL Request: '{mention['text']}' - Error: '{e.stderr.decode('utf-8')}'")
                if config.REPLY:
                    self.api.send_tweet(in_reply_to_status_id=mention["id"],
                                        auto_populate_reply_metadata=True,
                                        status=f"Sorry, I cannot process that request at the moment. Please try again later after {config.AUTHOR_TWITTER_HANDLE} fixes the issue.")

            latest_status = mention["id"]

        return latest_status

    def is_explicitly_mentioned(self, mention: dict, included_tweet: Optional[dict]) -> bool:
        mention_text: str = str(mention["text"]).lower()
        own_username: str = f"@{self.user_name}".lower()

        # If only one mention, then check if it's a reply to someone.
        if mention_text.count(own_username) == 1:
            # If Not A Reply, Accept (Since It Cannot Be An Implicit Mention Added By Twitter)
            is_reply: bool = False
            if "referenced_tweets" in mention and len(mention["referenced_tweets"]) > 0:
                for referenced_tweet in mention["referenced_tweets"]:
                    if referenced_tweet["type"] == "replied_to":
                        is_reply: bool = True

            # If Not Reply, Then Guaranteed Mention
            if not is_reply:
                return True

            # If No Included Tweet, Why Are We Here?
            if included_tweet is None:
                # TODO: Check How Many Includes Twitter Allows
                # self.logger.error(f"Somehow This Code Ran (Null Included Tweet In Non-Reply Tweet Check)!!! Tweet ID Is: {mention['id']}")
                return False

            # So, previous person mentioned the bot. Maybe not explicit, but enough to mostly accurately guess that this is not an explicit mention
            # The one exception is a chain of mention replies
            if str(included_tweet["text"]).lower().count(own_username) > 0:
                return False

            self.logger.log(self.VERBOSE,
                            "Own Name: {own_name}, Own ID: {own_id}".format(own_name=self.user_name,
                                                                            own_id=self.user_id))
            self.logger.debug(
                "Tweet with ID {id} Failed to Pass Filter: {json}".format(id=mention["id"], json=json.dumps(mention)))
            return False

        # At least one of the username showed up, so definitely a mention
        if mention_text.count(own_username) > 0:
            return True

        # No Mentions Showed Up, Should Never Have Been Read In To This Function
        self.logger.warning("Tweet with ID {id} With No Mention Showed Up In The Explicit Mention Check: {json}".format(
            id=mention["id"], json=json.dumps(mention)))
        return False

    def save_status_to_file(self, status_id: int):
        file_contents = {
            "last_status": status_id
        }

        f = open(self.status_file, "w")
        f.write(json.dumps(file_contents))
        f.close()

    def read_status_from_file(self) -> Optional[Any]:
        if not path.exists(self.status_file):
            return None

        f = open(self.status_file, "r")
        file_contents = f.read()
        f.close()

        # {"last_status": 1333984649056546816}
        try:
            decoded = json.loads(file_contents)

            if 'last_status' not in decoded:
                return None
        except JSONDecodeError:
            return None

        return decoded['last_status']
