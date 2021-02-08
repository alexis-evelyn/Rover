#!/usr/bin/python
import base64
import decimal
import distutils.util
import hashlib
import hmac
import json
import os
import time
from json import JSONDecodeError
from typing import Optional, List, Union

import sqlalchemy
from doltpy.core import Dolt

from archiver import config as archive_config
from rover import config, search_tweets
from database import database

from urllib.parse import urlparse, parse_qs

# Error Codes
# 1 - Invalid Endpoint
# 2 - No Account ID Specified
# 3 - No Results Found!!!
# 4 - Invalid Post Data
# 5 - Need A Valid Tweet ID
# 6 - No Tweet Found
# 7 - No Webhook Config Setup
# 8 - Need to Set A Webhook Parameter
# 9 - Credentials Not Setup

from rover.server import helper_functions


def handle_api(self):
    # Determine Reply and Send It
    send_reply(self=self)


def send_headers(self, content_length: int = 0):
    self.send_response(200)
    self.send_header("Content-type", "application/json")

    helper_functions.handle_tracking_cookie(self=self)
    helper_functions.send_standard_headers(self=self)
    self.send_header("Content-Length", content_length)

    if config.SEND_TIMING_HEADERS:
        self.send_header("Server-Timing", format_timings(timings=self.timings))

    self.end_headers()


def format_timings(timings: dict) -> str:
    header: str = "backend_total;dur={total_time};desc=Total,"
    total_time: decimal = 0

    exclude_from_total: List[str] = [
        "run_function", "retrieve_tweet_analyze", "analyze_tweet_only"
    ]

    sorted_timings: dict = {key: value for key, value in sorted(timings.items(), key=lambda item: item[1])}

    for key in reversed(sorted_timings):
        # https://docs.python.org/3/library/time.html#time.time
        current_time: decimal = sorted_timings[key][0] * 1000

        # To Exclude For Total
        if key not in exclude_from_total:
            total_time += current_time

        desc: str = f"{sorted_timings[key][1]}-{sorted_timings[key][2]}"
        header += f"{key};dur={current_time};desc={desc},"

    header = header.format(total_time=total_time)
    header = header[:-1]
    return header


def send_reply(self):
    url: urlparse = urlparse(self.path)
    queries: dict = parse_qs(url.query)

    response_dict: dict = run_function(self=self, url=url, queries=queries)

    # Stolen From: https://stackoverflow.com/a/36142844/6828099
    response: str = json.dumps(response_dict, sort_keys=True, default=str)
    content_length: int = len(response)

    # logger.debug(f"Content Length: {content_length}")

    # Determine Headers To Send and Send Them
    send_headers(self=self, content_length=content_length)

    self.wfile.write(bytes(response, "utf-8"))
    # self.close_connection = True


def run_function(self, url: urlparse, queries: dict) -> dict:
    timing_start: time = time.time()
    
    endpoints = {
        '/api': send_help,
        '/api/analytics': web_analytics,
        '/api/analyze': analyze_tweet,
        '/api/latest': load_latest_tweets,
        '/api/search': perform_search,
        '/api/accounts': lookup_account,
        '/api/webhooks': handle_webhook,
        '/api/tweet': retrieve_tweet
    }

    func = endpoints.get(url.path.rstrip('/'), invalid_endpoint)
    results: dict = func(self=self, queries=queries)

    self.timings["run_function"] = (time.time() - timing_start, len(self.timings), "FunctionChooser")
    return results


def load_latest_tweets(self, queries: dict) -> dict:
    """
        Load Latest Tweets. Can Be From Account And/Or Paged.
        :param self:
        :param table: Table To Query
        :param queries: GET Queries Dictionary
        :return: JSON Response
    """
    timing_start: time = time.time()
    max_responses: int = int(queries['max'][0]) if "max" in queries and validateRangedNumber(value=queries['max'][0],
                                                                                             minimum=0, maximum=20) else 20

    # TODO: Deprecate This And Reserve For Another Function
    # last_tweet_id: Optional[int] = int(queries['tweet'][0]) if "tweet" in queries and validateNumber(
    #     value=queries['tweet'][0]) else None

    # TODO: Add Ability To Read From RAM (Saved To By Rover and Us) Otherwise Load From File Then Database
    if not os.path.exists(archive_config.CACHE_FILE_PATH):
        self.logger.warning(f"Generating Cache File!!!")
        time_start: time = time.time()
        response: dict = helper_functions.save_cache_file(self=self, max_tweets=max_responses)
        time_end: time = time.time()

        self.logger.warning(f"Generating File Took {time_end - time_start} Seconds!!!")
    else:
        response: dict = helper_functions.load_cache_file(self=self, max_tweets=max_responses)

    self.timings["load_latest_tweets"] = (time.time() - timing_start, len(self.timings), "LatestTweets")
    return response


def lookup_account(self, queries: dict) -> dict:
    timing_start: time = time.time()
    
    if "account" not in queries:
        # TODO: Create A Proper Error Handler To Ensure Error Messages and IDs Are Standardized
        return {
            "error": "No Account ID Specified",
            "code": 2
        }

    # TODO: Implement Proper Way To Kill Abusers
    # To Prevent Hanging The Server
    max_results: int = 10

    # Results To Return
    results: dict = {"accounts": []}

    found_a_result: bool = False
    count: int = 0
    for account_id_str in queries["account"]:
        # Don't Let Above Max Results To Prevent Hanging
        if count >= max_results:
            break

        # Make Sure Always Counted
        count = count + 1

        account_id: int = int(account_id_str) if "account" in queries and validateNumber(value=account_id_str) else None

        # No Valid Id, So Skip
        if account_id is None:
            continue

        accounts: dict = database.retrieveAccountInfo(account_id=account_id)

        # No Results, So Skip
        if len(accounts) < 1:
            continue

        found_a_result: bool = True

        results["accounts"].append({
            "account_id": str(account_id),
            "first_name": accounts[0]["first_name"],
            "last_name": accounts[0]["last_name"],
            "handle": accounts[0]["twitter_handle"],
            "notes": accounts[0]["notes"]
        })

    if not found_a_result:
        self.timings["lookup_account_fail"] = (time.time() - timing_start, len(self.timings), "FailedLookupAccount")
        return {
            "error": "No Results Found!!!",
            "code": 3
        }

    self.timings["lookup_account"] = (time.time() - timing_start, len(self.timings), "LookupAccount")
    return results


def perform_search(self, queries: dict) -> dict:
    timing_start: time = time.time()
    
    original_search_text: str = queries["text"][0] if "text" in queries else ""
    regex: bool = bool(distutils.util.strtobool(queries["regex"][0])) if "regex" in queries else False

    search_phrase: str = search_tweets.convert_search_to_query(phrase=original_search_text,
                                                               regex=regex)  # r"^RT @[\w]:*"

    search_results: dict = convertIDsToString(
        results=database.search_tweets(search_phrase=search_phrase, table=self.tweets_table, regex=regex))
    tweet_count: int = database.count_tweets(search_phrase=search_phrase, table=self.tweets_table, regex=regex)

    self.timings["perform_search"] = (time.time() - timing_start, len(self.timings), "SearchTweets")
    return {
        "search_text": original_search_text,
        "regex": regex,
        "count": tweet_count,
        "results": search_results
    }


def send_help(self, queries: dict) -> dict:
    """
        Used To Indicate Existing API Endpoints
        :return: JSON Response With URLs
    """
    return {
        "endpoints": [
            {"/api": "Query List of Endpoints"},
            {"/api/latest": "Retrieve Newest Tweets"},
            {"/api/search": "Search For Tweets"},
            {"/api/accounts": "Lookup Account Info By ID"},
            {"/api/tweet": "Lookup Tweet By ID"}
        ],
        "note": "Future Description of Query Parameters Are On My Todo List"
    }


def invalid_endpoint(self, queries: dict) -> dict:
    """
        Used To Indicate Reaching an API Url That Doesn't Exist
        :return: JSON Error Message With Code For Machines To Process
    """
    return {
        "error": "Invalid Endpoint",
        "code": 1
    }


def handle_webhook(self, queries: dict) -> dict:
    timing_start: time = time.time()

    response: dict = {
        "error": "No Webhook Config Setup",
        "code": 7
    }

    if not os.path.exists(config.CONFIG_FILE_PATH):
        self.logger.error("No Webhook Config Setup!!!")
        self.timings["handle_webhook_fail"] = (time.time() - timing_start, len(self.timings), "FailedHandleWebhook")
        return response

    with open(file=config.CONFIG_FILE_PATH, mode="r") as f:
        config_contents: str = "\n".join(f.readlines())
        try:
            config_dict: dict = json.loads(s=config_contents)
        except JSONDecodeError:
            self.logger.error("Failed To JSON Decode Webhook Config!!!")
            self.timings["handle_webhook_fail"] = (time.time() - timing_start, len(self.timings), "FailedHandleWebhook")
            return response
        finally:
            if "webhooks" not in config_dict:
                return response

            config_ids: dict = config_dict["webhooks"]
            del config_contents
            del config_dict

    current_id: str = queries["id"][0] if "id" in queries else ""

    if current_id == "":
        self.timings["handle_webhook_fail"] = (time.time() - timing_start, len(self.timings), "FailedHandleWebhook")
        return {
            "error": "Need to Set A Webhook Parameter",
            "code": 8
        }

    if current_id not in config_ids.values():
        self.timings["handle_webhook_fail"] = (time.time() - timing_start, len(self.timings), "FailedHandleWebhook")
        return {
            "error": "Need to Set A Webhook Parameter",
            "code": 8
        }

    # Stolen From: https://www.geeksforgeeks.org/python-get-key-from-value-in-dictionary/
    key: str = list(config_ids.keys())[list(config_ids.values()).index(current_id)]

    if key == "dolt":
        return handle_dolt_webhook(self=self, timing_start=timing_start)
    elif key == "twitter":
        return handle_twitter_webhook(self=self, timing_start=timing_start, queries=queries)


def handle_twitter_webhook(self, timing_start: time, queries: dict) -> dict:
    crc_token: bytes = bytes(queries["crc_token"][0], "utf-8") if "crc_token" in queries else ""

    if crc_token == "":
        self.timings["handle_webhook_fail"] = (time.time() - timing_start, len(self.timings), "FailedHandleWebhook")
        return {
            "debug": "No CRC Token Specified"
        }

    response: dict = {
        "error": "Credentials Not Setup",
        "code": 9
    }

    if not os.path.exists(config.CREDENTIALS_FILE_PATH):
        self.timings["handle_webhook_fail"] = (time.time() - timing_start, len(self.timings), "FailedHandleWebhook")
        return response

    with open(config.CREDENTIALS_FILE_PATH, mode="r") as f:
        credentials_contents: str = "\n".join(f.readlines())
        try:
            credentials_dict: dict = json.loads(s=credentials_contents)
        except JSONDecodeError:
            self.logger.error("Failed To JSON Decode Webhook Credentials!!!")
            self.timings["handle_webhook_fail"] = (time.time() - timing_start, len(self.timings), "FailedHandleWebhook")
            return response
        finally:
            if "consumer" not in credentials_dict:
                self.timings["handle_webhook_fail"] = (time.time() - timing_start, len(self.timings), "FailedHandleWebhook")
                return response

            if "secret" not in credentials_dict["consumer"]:
                self.timings["handle_webhook_fail"] = (time.time() - timing_start, len(self.timings), "FailedHandleWebhook")
                return response

            consumer_secret: bytes = bytes(credentials_dict["consumer"]["secret"], "utf-8")
            del credentials_contents
            del credentials_dict

    # creates HMAC SHA-256 hash from incoming token and your consumer secret
    sha256_hash_digest = hmac.new(consumer_secret,
                                  msg=crc_token,
                                  digestmod=hashlib.sha256).digest()
    del consumer_secret

    # construct response data with base64 encoded hash
    response = {
        "response_token": f"sha256={base64.b64encode(sha256_hash_digest)}"
    }

    self.timings["handle_webhook"] = (time.time() - timing_start, len(self.timings), "HandleWebhook")
    return response


def handle_dolt_webhook(self, timing_start: time) -> dict:
    try:
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        webhook_body: dict = json.loads(post_data)

        response: dict = {
            "type": "unknown",
            "received": post_data.decode('utf-8')
        }

        if 'message' in webhook_body and webhook_body['message'] == "ping":
            response['type'] = "ping"
        elif 'head' in webhook_body and 'prev' in webhook_body:
            response['type'] = "push"

        # Logger Here?
        # For Ping To Verify Webhook Existence - {"message":"ping","repository":{"name":"presidential-tweets","owner":"alexis-evelyn"}}
        # Only Event As Of Time of Writing - {"ref":"refs/heads/master","head":"1pmuiljube6m238144qo69gvfra853uc","prev":"ro99bhicq8renuh3cectpfuaih8fp64p","repository":{"name":"corona-virus","owner":"dolthub"}}

        self.timings["handle_webhook"] = (time.time() - timing_start, len(self.timings), "HandleWebhook")
        return response
    except:
        self.timings["handle_webhook_fail"] = (time.time() - timing_start, len(self.timings), "FailedHandleWebhook")
        return {
            "error": "Invalid Post Data",
            "code": 4
        }


def retrieve_tweet(self, queries: dict) -> dict:
    timing_start: time = time.time()
    tweet_id: Optional[int] = int(queries['id'][0]) if "id" in queries and validateNumber(queries['id'][0]) else None

    response: dict = {
        "error": "Need A Valid Tweet ID",
        "code": 5
    }

    if tweet_id is None:
        return response

    tweet: dict = convertIDsToString(
        results=database.retrieveTweet(table=self.tweets_table, tweet_id=str(tweet_id),
                                       hide_deleted_tweets=False,
                                       only_deleted_tweets=False))

    if len(tweet) < 1:
        response: dict = {
            "error": "No Tweet Found",
            "code": 6
        }
    else:
        response: dict = {
            "results": tweet,
            "tweet_id": tweet[0]['id']
        }

    self.timings["retrieve_tweet"] = (time.time() - timing_start, len(self.timings), "RetrieveTweet")
    return response


# TODO: MOVE TO DATABASE SCRIPT
def web_analytics(self, queries: dict) -> dict:
    timing_start: time = time.time()
    analytics_engine: sqlalchemy.engine = self.analytics_engine
    # stmt = select(User.id).where(User.id.in_([1, 2, 3]))
    get_analytics: str = "select * from web order by date desc limit 30"

    result_proxy = analytics_engine.execute(get_analytics)
    results: List[dict] = [{column: value for column, value in row_proxy.items()} for row_proxy in result_proxy]

    # self.logger.error(f"Results: {results}")
    response: dict = {
        "results": results
    }

    self.timings["web_analytics"] = (time.time() - timing_start, len(self.timings), "WebAnalytics")
    return response


def analyze_tweet(self, queries: dict) -> dict:
    timing_start: time = time.time()
    tweet_id: Optional[int] = int(queries['id'][0]) if "id" in queries and validateNumber(queries['id'][0]) else None

    if tweet_id is None:
        return {
            "error": "Need A Valid Tweet ID",
            "code": 5
        }

    # Retrieve Tweet
    retrieve_tweet_start: time = time.time()
    tweet: List[dict] = database.retrieveTweet(table=self.tweets_table, tweet_id=str(tweet_id),
                                               hide_deleted_tweets=False,
                                               only_deleted_tweets=False)
    self.timings["retrieve_tweet_analyze"] = (time.time() - retrieve_tweet_start, len(self.timings), "RetrieveTweet")

    if len(tweet) < 1:
        return {
            "error": "No Tweet Found",
            "code": 6
        }

    # Analyze Tweet
    analyze_tweet_start: time = time.time()
    results: List[dict] = helper_functions.analyze_tweets(logger=self.logger, VERBOSE=self.VERBOSE, tweets=tweet)
    self.timings["analyze_tweet_only"] = (time.time() - analyze_tweet_start, len(self.timings), "AnalyzeTweet")

    response: dict = {
        "note": "Not Fully Implemented Yet",
        "results": results
    }

    self.timings["analyze_tweet"] = (time.time() - timing_start, len(self.timings), "TweetAnalysis")
    return response


def convertIDsToString(results: Union[List[dict], dict]):
    for result in results:
        result["twitter_user_id"] = str(result["twitter_user_id"])
        result["id"] = str(result["id"])

        # Account ID of Tweet That Was Retweeted
        if "retweetedUserId" in result:
            result["retweetedUserId"] = str(result["retweetedUserId"])

        # Tweet ID of Tweet That Was Retweeted
        if "retweetedTweetId" in result:
            result["retweetedTweetId"] = str(result["retweetedTweetId"])

    return results


def validateNumber(value: str) -> bool:
    if not value.isnumeric():
        return False

    return True


def validateRangedNumber(value: str, minimum: int = 0, maximum: int = 100) -> bool:
    if not value.isnumeric():
        return False

    number: int = int(value)

    if number > maximum or number < minimum:
        return False

    return True
