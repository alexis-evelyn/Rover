#!/usr/bin/python

import json
import logging
import re
from io import BytesIO
from json import JSONDecodeError
from re import Match
from typing import Optional, List

import requests
from doltpy.core.system_helpers import get_logger

from requests import Response
from requests_oauthlib import OAuth1


class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token: str):
        self.token = token

    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r


class TweetAPI2:
    def __init__(self, auth: BearerAuth, alt_auth: Optional[BearerAuth] = None, reply_auth: Optional[OAuth1] = None):
        self.logger: logging.Logger = get_logger(__name__)
        self.auth: BearerAuth = auth
        self.alt_auth: Optional[BearerAuth] = alt_auth
        self.reply_auth: Optional[OAuth1] = reply_auth
        self.user_agent = "Chrome/90"

    def get_tweet(self, tweet_id: str) -> Response:
        # To deal with some tweets breaking with entities.mentions.username
        expansions: str = "author_id,referenced_tweets.id,in_reply_to_user_id,attachments.media_keys,attachments.poll_ids,geo.place_id,referenced_tweets.id.author_id"

        params: dict = {
            "tweet.fields": "id,text,attachments,author_id,conversation_id,created_at,entities,geo,in_reply_to_user_id,lang,possibly_sensitive,public_metrics,referenced_tweets,source,withheld",
            "expansions": f"{expansions},entities.mentions.username",
            "media.fields": "media_key,type,duration_ms,height,preview_image_url,public_metrics,width",
            "place.fields": "full_name,id,contained_within,country,country_code,geo,name,place_type",
            "poll.fields": "id,options,duration_minutes,end_datetime,voting_status",
            "user.fields": "id,name,username,created_at,description,entities,location,pinned_tweet_id,profile_image_url,protected,public_metrics,url,verified,withheld"
        }

        # 1183124665688055809 = id
        api_url: str = 'https://api.twitter.com/2/tweets/{}'.format(tweet_id)
        tweet_response: Response = requests.get(url=api_url, params=params, auth=self.auth)

        try:
            tweet_json: dict = json.loads(tweet_response.text)
        except JSONDecodeError:
            self.logger.error("Failed To Decode JSON From Tweet Response!!!")
            return tweet_response

        if 'status' in tweet_json and tweet_json['status'] == 500:
            params["expansions"] = expansions
            return requests.get(url=api_url, params=params, auth=self.auth)

        return tweet_response

    def get_tweet_v1(self, tweet_id: str) -> Response:
        params: dict = {
            "id": tweet_id,
            "tweet_mode": "extended"
        }

        # 1340760721618063361 = id
        api_url: str = 'https://api.twitter.com/1.1/statuses/show.json'
        return requests.get(url=api_url, params=params, auth=self.auth)

    def get_mentions(self, screen_name: str, since_id: Optional[int] = None) -> Response:
        # https://api.twitter.com/2/tweets/search/recent?query=@DigitalRoverDog%20-from:DigitalRoverDog%20-is:retweet%20%20-is:quote%20to:DigitalRoverDog&max_results=100
        # @DigitalRoverDog -from:DigitalRoverDog -is:retweet -is:quote to:DigitalRoverDog

        params: dict = {
            "max_results": 100,
            "query": f"@{screen_name} -from:{screen_name} to:{screen_name} -is:retweet -is:quote",
            "tweet.fields": "attachments,author_id,context_annotations,conversation_id,created_at,entities,geo,id,in_reply_to_user_id,lang,possibly_sensitive,public_metrics,referenced_tweets,source,text,withheld",
            "expansions": "attachments.poll_ids,attachments.media_keys,author_id,geo.place_id,in_reply_to_user_id,referenced_tweets.id,entities.mentions.username,referenced_tweets.id.author_id",
            "media.fields": "duration_ms,height,media_key,preview_image_url,public_metrics,type,url,width",
            "place.fields": "contained_within,country,country_code,full_name,geo,id,name,place_type",
            "poll.fields": "duration_minutes,end_datetime,id,options,voting_status",
            "user.fields": "created_at,description,entities,id,location,name,pinned_tweet_id,profile_image_url,protected,public_metrics,url,username,verified,withheld"
        }

        if since_id is not None:
            params['since_id'] = since_id

        api_url: str = 'https://api.twitter.com/2/tweets/search/recent'
        return requests.get(url=api_url, params=params, auth=self.auth)

    def lookup_user_via_id(self, user_id: str) -> Response:
        # https://api.twitter.com/2/users/:id

        params: dict = {
            "user.fields": "created_at,description,entities,id,location,name,pinned_tweet_id,profile_image_url,protected,public_metrics,url,username,verified,withheld",
            "expansions": "pinned_tweet_id",
            "tweet.fields": "attachments,author_id,context_annotations,conversation_id,created_at,entities,geo,id,in_reply_to_user_id,lang,possibly_sensitive,public_metrics,referenced_tweets,source,text,withheld"
        }

        api_url: str = f'https://api.twitter.com/2/users/{user_id}'
        return requests.get(url=api_url, params=params, auth=self.auth)

    def lookup_tweets_via_timeline(self, user_id: str = None, screen_name: str = None,
                                   since_id: str = None) -> Response:
        params: dict = {
            "include_rts": "true",
            "exclude_replies": "false"
        }

        if since_id is not None:
            params['since_id'] = since_id

        person = False
        if user_id is not None:
            params['user_id'] = user_id
            person = True

        if screen_name is not None and not person:
            params['screen_name'] = screen_name
            person = True

        if not person:
            raise ValueError('You need to set either a user_id or screen_name. Not both, not neither')

        api_url: str = 'https://api.twitter.com/1.1/statuses/user_timeline.json'
        return requests.get(url=api_url, params=params, auth=self.auth)

    def lookup_tweets_via_search(self, user_id: Optional[str] = None, screen_name: Optional[str] = None,
                                 since_id: Optional[int] = None) -> Response:
        # https://api.twitter.com/2/tweets/search/recent?query=from:25073877&max_results=100&since_id=1336411597330391045

        params: dict = {
            "max_results": 100
        }

        if since_id is not None:
            params['since_id'] = since_id

        person = False
        if user_id is not None:
            params['query'] = f"from:{user_id}"
            person = True

        if screen_name is not None and not person:
            params['query'] = f"from:@{screen_name}"
            person = True

        if not person:
            raise ValueError('You need to set either a user_id or screen_name. Not both, not neither')

        # TODO: Remove - Temporary Means To Get Rid Of Bot Spam From @BidenInaugural
        if user_id == "1333168873860984832":
            filter_text: str = "We'll make sure you don't miss #Inauguration2021"
            params['query'] = params['query'] + f'-"{filter_text}"'

            filter_text: str = "We'll miss you!"
            params['query'] = params['query'] + f'-"{filter_text}"'

        api_url: str = 'https://api.twitter.com/2/tweets/search/recent'
        return requests.get(url=api_url, params=params, auth=self.auth)

    def stream_tweets(self) -> Response:
        params: dict = {
            "tweet.fields": "id,text,attachments,author_id,conversation_id,created_at,entities,geo,in_reply_to_user_id,lang,possibly_sensitive,public_metrics,referenced_tweets,source,withheld",
            "expansions": "author_id,referenced_tweets.id,in_reply_to_user_id,attachments.media_keys,attachments.poll_ids,geo.place_id,entities.mentions.username,referenced_tweets.id.author_id",
            "media.fields": "media_key,type,duration_ms,height,preview_image_url,public_metrics,width",
            "place.fields": "full_name,id,contained_within,country,country_code,geo,name,place_type",
            "poll.fields": "id,options,duration_minutes,end_datetime,voting_status",
            "user.fields": "id,name,username,created_at,description,entities,location,pinned_tweet_id,profile_image_url,protected,public_metrics,url,verified,withheld"
        }

        # 1183124665688055809 = id
        api_url: str = 'https://api.twitter.com/2/tweets/search/stream'
        return requests.get(url=api_url, params=params, auth=self.auth, stream=True)

    def get_guest_token(self) -> Optional[str]:
        if type(self.alt_auth) is not BearerAuth:
            return None

        headers: dict = {
            'User-Agent': self.user_agent
        }

        url: str = 'https://twitter.com/'

        response: Optional[str] = requests.get(url=url, headers=headers).text

        guest_token_regex = "gt=[0-9]*"

        # No Response - Return Nothing
        if type(response) is not str:
            return None

        guest_token_cookie: Optional[Match[str]] = re.search(guest_token_regex, response)

        # Missing Guest Token - Return Nothing
        if type(guest_token_cookie) is not Match:
            return None

        # Return Guest Token
        return str(guest_token_cookie[0].split('=')[1])

    def get_broadcast_json(self, stream_id: str, guest_token: str) -> Response:
        headers: dict = {
            'User-Agent': self.user_agent,
            'X-Guest-Token': guest_token
        }

        api_url: str = f'https://twitter.com/i/api/1.1/broadcasts/show.json?include_events=true&ids={stream_id}'
        return requests.get(url=api_url, headers=headers, auth=self.alt_auth)

    def get_stream_json(self, media_key: str, guest_token: str) -> Response:
        headers: dict = {
            'User-Agent': self.user_agent,
            'X-Guest-Token': guest_token
        }

        api_url: str = f'https://mobile.twitter.com/i/api/1.1/live_video_stream/status/{media_key}'
        return requests.get(url=api_url, headers=headers, auth=self.alt_auth)

    def upload_image(self, file: BytesIO):
        # multipart/form-data

        # Ensure Reading From Beginning Of File
        file.seek(0)
        image_contents: bytes = file.read()

        params: dict = {
            "media_category": "tweet_image"
        }

        files: dict = {
            "media": ('rover-media.png', image_contents, 'image/png')
        }

        api_url: str = 'https://upload.twitter.com/1.1/media/upload.json'
        return requests.post(url=api_url, params=params, files=files, auth=self.reply_auth)

    def send_tweet(self, status: str,
                   in_reply_to_status_id: Optional[str] = None,
                   auto_populate_reply_metadata: bool = True,
                   exclude_reply_user_ids: Optional[List[int]] = None,
                   media: Optional[BytesIO] = None):

        params: dict = {
            "status": status,
            "auto_populate_reply_metadata": str(auto_populate_reply_metadata)
        }

        if in_reply_to_status_id is not None:
            params["in_reply_to_status_id"] = in_reply_to_status_id

        if exclude_reply_user_ids is not None:
            params["exclude_reply_user_ids"] = exclude_reply_user_ids

        if media is not None:
            # media_ids, attachment_url
            media_response: Response = self.upload_image(file=media)

            try:
                media_json: dict = json.loads(media_response.text)

                if "media_id_string" in media_json:
                    params["media_ids"] = media_json["media_id_string"]
            except:
                pass

        api_url: str = 'https://api.twitter.com/1.1/statuses/update.json'
        return requests.post(url=api_url, params=params, auth=self.reply_auth)
