#!/bin/python3
import json
from json import JSONDecodeError
from typing import Optional

import requests
import re

from requests import Response


def save_page(url: str) -> str:
    form_url: str = f"https://web.archive.org/save/{url}"
    # form_data: dict = {
    #     "url": url,
    #     "capture_all": "on"
    # }
    #
    # headers: dict = {
    #     "User-Agent": "Chrome/90",
    #     "Referer": "https://web.archive.org/save",
    #     "Origin": "https://web.archive.org"
    # }

    # response: Response = requests.post(url=form_url, data=form_data, headers=headers)  # Doesn't Work - Probably Due To Needing Javascript
    response: Response = requests.get(url=form_url)  # Works
    # print(response.history)
    # print(response.headers)
    return response.url


def check_page(url: str) -> Optional[str]:
    api_url: str = "https://archive.org/wayback/available"

    # TODO: Strip `https://` off of the URL before lookup?
    # stripped_url: str = re.sub(r'http[s]*://', '', url)
    # stripped_url: str = re.sub(r'www.', '', stripped_url)

    parameters: dict = {
        "url": url
    }

    response: Response = requests.get(url=api_url, params=parameters)

    try:
        data: dict = json.loads(response.text)

        if "archived_snapshots" in data and "closest" in data["archived_snapshots"]:
            return data["archived_snapshots"]["closest"]["url"]

        return None
    except JSONDecodeError:
        return None


if __name__ == "__main__":
    url: str = "https://twitter.com/FLOTUS/status/1359601608607346695"

    print(f"Checking If Page Archived: {url}")
    checked: Optional[str] = check_page(url=url)
    if checked is None:
        print(f"Nope, Saving Page: {url}")
        saved: str = save_page(url=url)
        print(f"Saved At: {saved}")
    else:
        print(f"Yep, Page At: {checked}")
