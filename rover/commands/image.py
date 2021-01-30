#!/usr/bin/python

import os
import random

import twitter

from PIL import Image, ImageDraw, ImageFont

from archiver.tweet_api_two import TweetAPI2
from rover import config


def draw_image(api: TweetAPI2, status: dict):
    if not os.path.exists(config.WORKING_DIRECTORY):
        os.makedirs(config.WORKING_DIRECTORY)

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
        fnt = ImageFont.truetype(config.FONT_PATH, config.FONT_SIZE)
        length = int(config.IMAGE_NAME_OFFSET_MULTIPLIER * len(config.IMAGE_NAME))
        draw.multiline_text((im.size[0] - length, im.size[1] - 50), config.IMAGE_NAME, font=fnt,
                            fill=(int(255 - r), int(255 - g), int(255 - b)))

        # write to file like object
        # output = io.BytesIO()  # Why does the PostUpdate not work with general bytesio?
        im.save(config.TEMPORARY_IMAGE_PATH, config.TEMPORARY_IMAGE_FORMAT)

        new_status = "@{user}".format(user=status["author_user_name"])

        if config.REPLY:
            api.send_tweet(in_reply_to_status_id=status["id"], status=new_status, media=config.TEMPORARY_IMAGE_PATH)

        os.remove(config.TEMPORARY_IMAGE_PATH)  # Remove temporary file
