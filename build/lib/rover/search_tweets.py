#!/usr/bin/python
import json
import html

from requests import Response
from archiver.tweet_api_two import TweetAPI2
from mysql.connector import conversion
from typing import Optional


def convert_search_to_query(phrase: str, regex: bool = False) -> str:
    # Use MySQL Library For Escaping Search Text
    sql_converter: conversion.MySQLConverter = conversion.MySQLConverter()
    phrase = sql_converter.escape(value=phrase)

    phrase = phrase.replace(r"\'", r"'")  # This gets fixed later by PyPika
    if not regex:
        phrase = phrase.replace(' ', '%')
        phrase = '%' + phrase + '%'

    return phrase


def get_username_by_id(api: TweetAPI2, author_id: int) -> Optional[str]:
    user: Response = api.lookup_user_via_id(user_id=str(author_id))

    response: dict
    try:
        response = json.loads(user.text)
    except:
        return None

    if "data" not in response or "username" not in response["data"]:
        return None

    return response["data"]["username"]


def get_search_keywords(text: str, search_word_query: str = 'search') -> str:
    # no_mentions = re.sub('@[A-Za-z0-9]+', '', text)
    # no_trailing_spaces = no_mentions.lstrip().rstrip()
    # no_trailing_search_command = no_trailing_spaces.lstrip('search').lstrip()

    search_word_pos: int = text.find(search_word_query) + len(search_word_query)
    post_search_phrase: str = text[search_word_pos:]
    no_trailing_spaces = post_search_phrase.lstrip().rstrip()
    fix_html_escape = html.unescape(no_trailing_spaces)

    return fix_html_escape


class SafeDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'
