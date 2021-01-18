#!/usr/bin/python

import json
import logging
import threading
import time
from typing import Optional, Any, Reversible
from json.decoder import JSONDecodeError
from os import path

import twitter
from doltpy.core import DoltException
from doltpy.core.system_helpers import get_logger
from twitter import TwitterError

from rover import handle_commands, config
from config import config as main_config


class Rover(threading.Thread):
    def __init__(self, threadID: int, name: str, threadLock: threading.Lock, requested_wait_time: int = 60, reply: bool = True):
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

        # TODO: Figure Out How To Automatically Determine This
        self.user_id: int = config.TWITTER_USER_ID
        self.user_name: str = config.TWITTER_USER_HANDLE

        # Debugging Paths
        self.logger.info("Working Directory: {working_directory}".format(working_directory=config.WORKING_DIRECTORY))

        # Setup For Twitter API
        with open(self.credentials_file, "r") as file:
            self.__credentials: dict = json.load(file)

    def run(self):
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

        if replied_to_status is not None:
            self.save_status_to_file(replied_to_status)

    def process_tweet(self, latest_status: int = None) -> int:
        api = twitter.Api(consumer_key=self.__credentials['consumer']['key'],
                          consumer_secret=self.__credentials['consumer']['secret'],
                          access_token_key=self.__credentials['token']['key'],
                          access_token_secret=self.__credentials['token']['secret'],
                          sleep_on_rate_limit=True,
                          tweet_mode="extended")

        mentions: Reversible[json] = api.GetMentions(since_id=latest_status)
        # mentions: Reversible[json] = api.GetStatuses(status_ids=[1334461310734659584, 1334465300243345408, 1334466433368137729, 1335104236129046528, 1335109553088831489, 1335110267932438528])  # For Debugging Bot
        # mentions = api.GetStatuses(status_ids=[1335104236129046528])

        latest_status = None
        for mention in reversed(mentions):
            # Don't Respond To Own Tweets (870156302298873856 is user id for @DigitalRoverDog)
            if mention.user.id == self.user_id:
                continue

            # To Prevent Implicit Replying (So the bot only replies to explicit requests)
            if not self.is_explicitly_mentioned(mention=mention):
                continue

            self.logger.log(self.INFO_QUIET,
                            "Responding To Tweet From @{user}: {text}".format(user=mention.user.screen_name,
                                                                              text=mention.full_text))

            try:
                handle_commands.process_command(api=api, status=mention,
                                                info_level=self.INFO_QUIET,
                                                verbose_level=self.VERBOSE)
            except TwitterError as e:
                self.log_twitter_error(error=e)
            except DoltException as e:
                self.logger.error(f"Failed To Process SQL Request: '{mention.text}' - Error: '{e.stderr.decode('utf-8')}'")
                if config.REPLY:
                    try:
                        api.PostUpdate(in_reply_to_status_id=mention.id,
                                       auto_populate_reply_metadata=True,
                                       status=f"Sorry, I cannot process that request at the moment. Please try again later after {config.AUTHOR_TWITTER_HANDLE} fixes the issue.")
                    except TwitterError as e:
                        self.log_twitter_error(error=e)

            latest_status = mention.id

        return latest_status

    def log_twitter_error(self, error: TwitterError):
        # To Deal With That Duplicate Status Error - [{'code': 187, 'message': 'Status is a duplicate.'}]
        # [{'message': 'Over capacity', 'code': 130}]
        if type(error.message) is dict:
            self.logger.error("Twitter Error (Code {code}): {error_message}".format(code=error.message["code"],
                                                                                    error_message=error.message["message"]))
        else:
            self.logger.error("Twitter Error: {error_message}".format(error_message=error.message))

    def is_explicitly_mentioned(self, mention: json) -> bool:
        # If the mention shows up more than once, return true. Twitter adds one implicit reply when replying to a user,
        # but if more than one mention exists, then it's a guaranteed explicit mention.
        if mention.full_text.startswith(self.user_name + " ") and mention.full_text.count(self.user_name) == 1:
            # If Not A Reply, Accept (Since It Cannot Be An Implicit Mention Added By Twitter)
            if mention.in_reply_to_status_id is None:
                return True

            # 1334465300243345408 should pass, 1335110267932438528 should fail
            # Pass means that the method returns true
            # AFAICT, there's no way to filter between these two test cases atm

            self.logger.log(self.VERBOSE,
                            "Own Name: {own_name}, Own ID: {own_id}".format(own_name=self.user_name,
                                                                            own_id=self.user_id))
            self.logger.debug("Tweet with ID {id} Failed to Pass Filter: {json}".format(id=mention.id, json=mention))
            return False

        return True

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
