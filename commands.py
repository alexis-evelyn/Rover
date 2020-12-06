#!/usr/bin/python
import io
import json
import logging
import os
import random
import time
import ast

import twitter
from PIL import Image, ImageDraw, ImageFont
from doltpy.core import Dolt

logger: logging.Logger = None


def process_command(api: twitter.Api, status: twitter.models.Status, logger_param: logging.Logger):
    global logger
    logger = logger_param

    if "image" in status.text:
        draw_image(api=api, status=status)
    elif "hello" in status.text:
        say_hello(api=api, status=status)
    elif "search" in status.text:
        search_text(api=api, status=status)


def draw_image(api: twitter.Api, status: twitter.models.Status):
    if not os.path.exists('working'):
        os.makedirs('working')

    with Image.new("RGB", (1024, 1024)) as im:
        draw = ImageDraw.Draw(im)

        # random.seed(time.time())
        r = random.random() * 255
        g = random.random() * 255
        b = random.random() * 255

        for x in range(0, im.size[0]):
            for y in range(0, im.size[0]):
                im.putpixel((x, y), (int(random.random() * r), int(random.random() * g), int(random.random() * b)))

        # draw.line((0, 0) + im.size, fill=128)
        # draw.line((0, im.size[1], im.size[0], 0), fill=128)

        # αℓєχιѕ єνєℓуη 🏳️‍⚧️ 🏳️‍🌈
        # Zero Width Joiner (ZWJ) does not seem to be supported, need to find a font that works with it to confirm it
        # fnt = ImageFont.truetype("working/symbola/Symbola-AjYx.ttf", 40)
        fnt = ImageFont.truetype("working/firacode/FiraCode-Bold.ttf", 40)
        name = "Digital Rover"  # status.user.name
        length = int(25.384615384615385 * len(name))
        draw.multiline_text((im.size[0] - length, im.size[1] - 50), name, font=fnt,
                            fill=(int(255 - r), int(255 - g), int(255 - b)))

        # write to file like object
        # output = io.BytesIO()  # Why does the PostUpdate not work with general bytesio?
        im.save("working/temp.png", "PNG")

        new_status = "@{user}".format(user=status.user.screen_name)
        api.PostUpdate(in_reply_to_status_id=status.id, status=new_status, media="working/temp.png")
        os.remove("working/temp.png")  # Remove temporary file


def say_hello(api: twitter.Api, status: twitter.models.Status):
    new_status = "@{user} Hello {name}".format(name=status.user.name, user=status.user.screen_name)
    api.PostUpdate(in_reply_to_status_id=status.id, status=new_status)


def search_text(api: twitter.Api, status: twitter.models.Status):
    # Broken For Some Reason
    # select id, text from trump where text COLLATE utf8mb4_unicode_ci like '%sleepy%joe%' order by id desc limit 10;
    # select count(id) from trump where text COLLATE utf8mb4_unicode_ci like '%sleepy%joe%';

    # select id, text from trump where lower(text) COLLATE utf8mb4_unicode_ci like lower('%sleepy%joe%') order by id desc limit 10;
    # select count(id) from trump where lower(text) COLLATE utf8mb4_unicode_ci like lower('%sleepy%joe%');

    original_phrase = "Sleepy Joe"

    repo: Dolt = Dolt('working/presidential-tweets')
    phrase = convert_search_to_query(original_phrase)

    search_query = '''
        select * from trump where lower(text) COLLATE utf8mb4_unicode_ci like lower('{phrase}') order by id desc limit 10;
    '''.format(phrase=phrase)

    count_search_query = '''
        select count(id) from trump where lower(text) COLLATE utf8mb4_unicode_ci like lower('{phrase}');
    '''.format(phrase=phrase)

    count_result = repo.sql(query=count_search_query, result_format="json")["rows"]
    search_results = repo.sql(query=search_query, result_format="json")["rows"]
    # Load and Convert JSON in JSON Column - json.loads(results[0]["json"])

    count = -1
    for header in count_result[0]:
        count = count_result[0][header]
        logger.debug("Count For Phrase \"{search_phrase}\": {count}".format(search_phrase=original_phrase, count=count))
        break

    for result in search_results:
        logger.debug("Example Tweet For Phrase \"{search_phrase}\": {tweet_id} - {tweet_text}".format(
            search_phrase=original_phrase, tweet_id=result["id"], tweet_text=result["text"]))

    search_post_response = search_results[0]
    author = get_username_by_id(api=api, author_id=json.loads(search_post_response["json"])["data"]["author_id"])
    url = "https://twitter.com/{screen_name}/statuses/{status_id}".format(status_id=search_post_response["id"],
                                                                          screen_name=author)

    if count == 1:
        word_times = "time"
    else:
        word_times = "times"

    new_status = "@{user} @{screen_name} has tweeted about \"{search_phrase}\" {search_count} {word_times}. The latest example is at {status_link}".format(
        user=status.user.screen_name, status_link=url, search_phrase=original_phrase, screen_name=author,
        search_count=count, word_times=word_times)

    api.PostUpdate(in_reply_to_status_id=status.id, status=new_status)
    logger.warn("Sending Status: {new_status}".format(new_status=new_status))


def convert_search_to_query(phrase: str) -> str:
    phrase = phrase.replace(' ', '%')
    phrase = '%' + phrase + '%'

    return phrase


def get_username_by_id(api: twitter.Api, author_id: int) -> str:
    user: twitter.models.User = api.GetUser(user_id=author_id)
    return user.screen_name
