#!/usr/bin/python
import datetime
import json
import random
import uuid

from http.server import BaseHTTPRequestHandler
from logging import Logger
from typing import List, Optional, Tuple
from distutils.util import strtobool

from archiver import config as archiver_config
from database import database
from rover import config
from rover.hostility_analysis import HostilityAnalysis
from rover.server.api_handler import lookup_account, convertIDsToString


def handle_tracking_cookie(self) -> Optional[Tuple[str, str]]:
    if "DNT" in self.headers and self.headers["DNT"] == "1":
        self.send_header("Set-Cookie",
                         "analytics=honor_dnt;expires=Thu, 01 Jan 1970 00:00:00 GMT,session=honor_dnt;expires=Thu, 01 Jan 1970 00:00:00 GMT")
        return

    expires = datetime.datetime.utcnow() + datetime.timedelta(days=30)  # expires in 30 days
    expire_time: str = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

    uuid_tracking: uuid.UUID = uuid.uuid4()
    uuid_session: str = str(random.sample(range(1, 1000000), 1)[0])

    # For If Debugging Via Localhost (Chrome Marks SameSite As None Being A Warning If Secure Is Not Set)
    _, ip_source = get_ip_address(self=self)
    secure: str = " Secure; SameSite=None" if ip_source != "Direct" else ""

    cookies: Optional[dict] = get_cookies(self=self)
    if cookies is not None:
        if 'analytics' in cookies and 'session' in cookies:
            return cookies['analytics'], cookies['session']
        elif 'analytics' in cookies:
            self.send_header("Set-Cookie", f"session={uuid_session};path=/; HttpOnly;{secure}")
            return None
        elif 'session' in cookies:
            self.send_header("Set-Cookie",
                             f"analytics={uuid_tracking};expires={expire_time};path=/; HttpOnly;{secure}")
            return None

    self.send_header("Set-Cookie",
                     f"analytics={uuid_tracking};expires={expire_time},session={uuid_session};path=/; HttpOnly;{secure}")


def get_cookies(self) -> Optional[dict]:
    if "cookie" in self.headers:
        cookies_split: List[str] = self.headers['cookie'].split(';')
        cookies: dict = {}

        for cookie_split in cookies_split:
            cookie: List[str] = cookie_split.strip().split('=')

            try:
                cookies[cookie[0]] = cookie[1]
            except IndexError as e:
                self.logger.error(f"Cookie Parse Error (IndexError): {cookie}")

        return cookies
    return None


def get_ip_address(self) -> Tuple[str, str]:
    # Cloudflare Forwarded IP
    if 'CF-Connecting-IP' in self.headers:
        ip_address: str = self.headers["CF-Connecting-IP"]
        ip_source: str = "Cloudflare"
    # NGinx Forwarded IP
    elif 'X-Real-IP' in self.headers:
        ip_address: str = self.headers["X-Real-IP"]
        ip_source: str = "NGinx"
    # Direct IP Connecting To This Server
    else:
        ip_address: str = str(self.client_address[0])
        ip_source: str = "Direct"

    return ip_address, ip_source


def send_standard_headers(self):
    # Performance Headers
    if "Service-Worker-Navigation-Preload" in self.headers:
        self.send_header("Vary", "Service-Worker-Navigation-Preload")

    # Security Headers
    self.send_header("X-Content-Type-Options", "nosniff")
    self.send_header("X-XSS-Protection", "1; mode=block")
    self.send_header("X-Frame-Options", "DENY")

    # Debug Headers
    ip_address, ip_source = get_ip_address(self=self)
    self.send_header("X-REQUESTED-PATH", str(self.path))
    self.send_header("X-YOUR-IP", ip_address)
    self.send_header("X-YOUR-IP-SOURCE", ip_source)

    # TODO: Add CONTENT-SECURITY-POLICY and CONTENT-SECURITY-POLICY-REPORT-ONLY From https://www.immuniweb.com/websec/?id=FjR5kcVe
    # TODO: Add Cookie Notice On Site Too. Use JS Cookie To Mark Notice Read
    # self.send_header("CONTENT-SECURITY-POLICY", "...")
    # self.send_header("CONTENT-SECURITY-POLICY-REPORT-ONLY", "...")

    if config.ALLOW_CORS:
        self.send_header("Access-Control-Allow-Origin", config.CORS_SITES)

    if config.ENABLE_HSTS:
        self.send_header("Strict-Transport-Security", config.HSTS_SETTINGS)


def save_cache_file(self, max_tweets: int = 20):
    # TODO: Add Ability To Pop Oldest Tweet And Append Latest One If File Exists
    latest_tweets: dict = convertIDsToString(database.latest_tweets(repo=self.repo, table=config.ARCHIVE_TWEETS_TABLE,
                                                                    max_responses=max_tweets))

    # TODO: Implement Proper Parsing On Javascript Side
    # To deal with Javascript JSON Parsing Fail Due To Too Long of A String
    for result in latest_tweets:
        try:
            del result['json']
        except KeyError:
            continue

    response: dict = {
        "results": latest_tweets
    }

    if len(latest_tweets) > 0:
        twitter_account_ids: List[str] = [tweet['twitter_user_id'] for tweet in latest_tweets]

        deduped_twitter_account_ids: List[str] = []
        [deduped_twitter_account_ids.append(account_id) for account_id in twitter_account_ids if
         account_id not in deduped_twitter_account_ids]

        account_info: dict = lookup_account(self=self, repo=self.repo, table=config.ARCHIVE_TWEETS_TABLE,
                                            queries={"account": deduped_twitter_account_ids})

        response["accounts"] = account_info["accounts"]
        response['latest_tweet_id'] = latest_tweets[0]['id']

    with open(file=archiver_config.CACHE_FILE_PATH, mode="w+") as cache:
        cache.writelines(json.dumps(response, sort_keys=True, default=str))
        cache.close()

    return response


def load_cache_file(self, max_tweets: int = 20) -> dict:
    with open(file=archiver_config.CACHE_FILE_PATH, mode="r") as cache:
        cache_body: List[str] = cache.readlines()
        response: dict = json.loads("\n".join(cache_body))

    return response


def analyze_tweets(logger: Logger, VERBOSE: int, tweets: List[dict]):
    # Instantiate Text Processor
    analyzer: HostilityAnalysis = HostilityAnalysis(logger_param=logger, verbose_level=VERBOSE)

    # Load Tweets To Analyze
    for result in tweets:
        logger.log(VERBOSE, "Adding Tweet For Processing: {tweet_id} - {tweet_text}".format(tweet_id=result["id"],
                                                                                            tweet_text=result["text"]))
        analyzer.add_tweet_to_process(result)

    analyzer.preprocess_tweets()
    return analyzer.process_tweets()


def should_track(headers: BaseHTTPRequestHandler.MessageClass):
    if "DNT" in headers and bool(strtobool(headers["DNT"])):
        return False
    return True
