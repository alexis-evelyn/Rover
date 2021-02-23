#!/usr/bin/python
import os
import json
import requests

from typing import List

# https://api.twitter.com/2/tweets/search/recent?query=conversation_id:1363824952617664512&tweet.fields=in_reply_to_user_id,author_id,created_at,conversation_id&max_results=100&until_id=1363868229567930376

bearer_token: str = "REDACTED"


class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token: str):
        self.token = token

    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r


token: BearerAuth = BearerAuth(token=bearer_token)

directory: str = "working/antislavery"

files: List[str] = [
    "slavery-1.json",
    "slavery-2.json",
    "slavery-3.json",
    # "slavery-4.json",
    # "slavery-5.json"
]

usernames: dict = {}
urls: List[str] = []


def lookup_username(author_id: str) -> str:
    api_url: str = f"https://api.twitter.com/2/users/{author_id}"
    author_request: requests = requests.get(url=api_url, auth=token)
    author_text: str = author_request.text
    author_dict: dict = json.loads(author_text)

    return author_dict["data"]["username"]


for file in files:
    print(f"Reading {file}")

    with open(file=os.path.join(directory, file), mode="r") as f:
        tweets: dict = json.loads("\n".join(f.readlines()))

        for tweet in tweets["data"]:
            tweet_id: str = tweet["id"]
            author_id: str = tweet["author_id"]

            if author_id not in usernames:
                # print(f"Looking Up Author ID: {author_id}")
                username: str = lookup_username(author_id=author_id)

                # print(f"{author_id} is {username}!!!")
                usernames[author_id] = username

            # print(f"Tweet: {tweet_id} - Author: {usernames[author_id]}")
            # https://twitter.com/FLOTUS/status/1359601608607346695?failedScript=polyfills
            url: str = f"https://twitter.com/{usernames[author_id]}/status/{tweet_id}"
            archive_url: str = f"https://web.archive.org/save/{url}?failedScript=polyfills"
            urls.append(archive_url)

            print(f"URL: {url} - Archive: {archive_url}")


with open(os.path.join(directory, "archive-me.txt"), mode="w+") as f:
    for entry in urls:
        f.write(entry + "\n")

    f.close()