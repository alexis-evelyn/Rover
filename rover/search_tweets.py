#!/usr/bin/python

import twitter
from mysql.connector import conversion
import html


def convert_search_to_query(phrase: str) -> str:
    # Use MySQL Library For Escaping Search Text
    sql_converter: conversion.MySQLConverter = conversion.MySQLConverter()
    phrase = sql_converter.escape(value=phrase)

    phrase = phrase.replace(' ', '%')
    phrase = phrase.replace(r"\'", r"'")  # This gets fixed later by PyPika
    phrase = '%' + phrase + '%'

    return phrase


def get_username_by_id(api: twitter.Api, author_id: int) -> str:
    user: twitter.models.User = api.GetUser(user_id=author_id)
    return user.screen_name


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
