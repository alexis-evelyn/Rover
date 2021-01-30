#!/usr/bin/python
import re
import urllib.parse
from re import Pattern, Match
from typing import List, Optional, Tuple

from database import database
from rover import config

from datetime import datetime
from json.decoder import JSONDecodeError
from pathlib import Path
from xml.etree.ElementTree import Element, tostring

import json
import traceback
import pytz
import pandas as pd
import subresource_integrity as integrity

from rover.server import helper_functions


def load_page(self, page: str):
    # Site Data
    site_title: str = "Rover"

    # TODO: Verify If Multiple Connections Can Cause Data Loss (It Can't Read Only, Maybe For Writing)
    data: dict = database.pickRandomOfficials(repo=self.repo)

    # Twitter Metadata
    twitter_title: str = site_title
    twitter_description: str = "Future Analysis Website Here" \
                               " For Officials Such As {official_one}," \
                               " {official_two}, and {official_three}" \
        .format(official_one=(data[0]["first_name"] + " " + data[0]["last_name"]),
                official_two=(data[1]["first_name"] + " " + data[1]["last_name"]),
                official_three=(data[2]["first_name"] + " " + data[2]["last_name"]))

    # twitter_description: str = "Future Analysis Website Here For Officials Such As Donald Trump, Joe Biden, and Barack Obama"

    # HTTP Headers
    self.send_response(200)
    self.send_header("Content-type", "text/html")

    helper_functions.handle_tracking_cookie(self=self)
    helper_functions.send_standard_headers(self=self)
    self.end_headers()

    # Header
    write_header(self=self, site_title=site_title, twitter_title=twitter_title, twitter_description=twitter_description)

    # Body
    write_body(self=self, page=page)

    # Footer
    write_footer(self=self)


def load_file(self, path: str, mime_type: str):
    # HTTP Headers
    self.send_response(200)
    self.send_header("Content-type", mime_type)

    helper_functions.handle_tracking_cookie(self=self)
    helper_functions.send_standard_headers(self=self)
    self.end_headers()

    # Load File
    self.wfile.write(load_binary_file(path=path))


def load_text_file(path: str) -> str:
    with open(path, "r") as file:
        file_contents = file.read()
        file.close()

        return file_contents


def load_binary_file(path: str) -> bytes:
    return Path(path).read_bytes()


def load_404_page(self, error_code: int = 404):
    self.send_response(error_code)
    self.send_header("Content-type", "text/html")

    helper_functions.handle_tracking_cookie(self=self)
    helper_functions.send_standard_headers(self=self)
    self.end_headers()

    # Header
    write_header(self=self, site_title="404 - Page Not Found", twitter_title="Page Not Found",
                 twitter_description="No Page Exists Here")

    # 404 Page Body - TODO: Add In Optional Variable Substitution Via write_body(...)
    self.wfile.write(
        bytes(load_text_file("rover/server/web/pages/errors/404.html").replace("{path}", self.path), "utf-8"))

    # Footer
    write_footer(self=self)


def load_offline_page(self):
    self.send_response(200)
    self.send_header("Content-type", "text/html")

    helper_functions.handle_tracking_cookie(self=self)
    helper_functions.send_standard_headers(self=self)
    self.end_headers()

    title: str = "Currently Offline"
    description: str = "Cannot Load Page Due Being Offline"

    # Header
    write_header(self=self, site_title=title, twitter_title=title, twitter_description=description)

    # Body
    write_body(self=self, page='errors/offline')

    # Footer
    write_footer(self=self)


def write_header(self, site_title: str, twitter_title: str, twitter_description: str):
    current_time: str = f"{datetime.now().astimezone(tz=pytz.UTC):%A, %B, %d %Y at %H:%M:%S.%f %z}"
    google_analytics_code: str = self.config["google_analytics_code"]

    # Files To Generate SRI Hashes For
    stylesheet_css: bytes = load_binary_file(path="rover/server/web/css/stylesheet.css")
    main_js: bytes = load_binary_file(path="rover/server/web/scripts/main.js")
    helper_js: bytes = load_binary_file(path="rover/server/web/scripts/helper.js")

    # SRI Hashes
    algorithms: Tuple[str] = ("sha512",)
    stylesheet_css_hash = integrity.render(data=stylesheet_css, algorithms=algorithms)
    main_js_hash = integrity.render(data=main_js, algorithms=algorithms)
    helper_js_hash = integrity.render(data=helper_js, algorithms=algorithms)

    self.wfile.write(bytes(load_text_file("rover/server/web/templates/header.html")
                           .replace("{site_title}", site_title)
                           .replace("{twitter_title}", twitter_title)
                           .replace("{twitter_handle}", config.AUTHOR_TWITTER_HANDLE)
                           .replace("{twitter_description}", twitter_description)
                           .replace("{current_time}", current_time)
                           .replace("{google_analytics_code}", google_analytics_code)
                           .replace("{github_repo}", config.GITHUB_REPO)
                           .replace("{website_root}", config.WEBSITE_ROOT)

                           # SRI Hash Integrity
                           .replace("{stylesheet_css_integrity}", stylesheet_css_hash)
                           .replace("{main_js_integrity}", main_js_hash)
                           .replace("{helper_js_integrity}", helper_js_hash)
                           , "utf-8"))


def write_body(self, page: str):
    self.wfile.write(bytes(load_text_file(f"rover/server/web/pages/{page}.html"), "utf-8"))


def write_footer(self):
    self.wfile.write(bytes(load_text_file("rover/server/web/templates/footer.html"), "utf-8"))


def load_tweet(self):
    # Validate URL First
    tweet_id: str = str(self.path).lstrip("/").rstrip("/").replace("tweet/", "").split("/")[0]

    # If Invalid Tweet ID
    if not tweet_id.isnumeric():
        return load_404_page(self=self)

    table: str = config.ARCHIVE_TWEETS_TABLE
    try:
        tweet: dict = database.retrieveTweet(repo=self.repo, table=table, tweet_id=tweet_id, hide_deleted_tweets=False,
                                             only_deleted_tweets=False)
    except JSONDecodeError as e:
        self.logger.error(f"JSON Decode Error While Retrieving Tweet: {tweet_id} - Error: {e}")
        self.logger.error({traceback.format_exc()})

        tweet: dict = {}

    # If Tweet Not In Database - Return A 404
    if len(tweet) < 1:
        return load_404_page(self=self)

    # Tweet Data
    tweet_text: str = str(tweet[0]['text'])
    account_id: int = tweet[0]['twitter_user_id']
    account_info: dict = database.retrieveAccountInfo(repo=self.repo, account_id=account_id)[0]
    account_name: str = "{first_name} {last_name}".format(first_name=account_info["first_name"],
                                                          last_name=account_info["last_name"])

    # Site Data
    site_title: str = "Tweet By {account_name}".format(account_name=account_name.replace('\"', '&quot;'))

    # Twitter Metadata
    twitter_title: str = site_title
    twitter_description: str = "{tweet_text}".format(tweet_text=tweet_text.replace('\"', '&quot;'))

    # HTTP Headers
    self.send_response(200)
    self.send_header("Content-type", "text/html")

    helper_functions.handle_tracking_cookie(self=self)
    helper_functions.send_standard_headers(self=self)
    self.end_headers()

    # Header
    write_header(self=self, site_title=site_title, twitter_title=twitter_title, twitter_description=twitter_description)

    # Body
    # write_body(self=self, page="single-tweet")
    self.wfile.write(bytes(load_text_file(f"rover/server/web/pages/single-tweet.html")
                           .replace("{tweet_json}", json.dumps(tweet[0]))
                           .replace("{twitter_account}", account_name)
                           .replace("{tweet_text}", tweet_text)
                           .replace("{device}", tweet[0]['device'])
                           , "utf-8"))

    # Footer
    write_footer(self=self)


def dict_to_xml(root_tag: str, iter_tag: str, urls: List[dict]):
    # xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
    root: Element = Element(root_tag)
    root.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

    for url in urls:
        iter_xml: Element = Element(iter_tag)

        for key in url:
            child: Element = Element(key)
            child.text = str(url[key])
            iter_xml.append(child)

        root.append(iter_xml)

    return root


def load_sitemap(self):
    # HTTP Headers
    self.send_response(200)
    self.send_header("Content-type", "application/xml")

    helper_functions.handle_tracking_cookie(self=self)
    helper_functions.send_standard_headers(self=self)
    self.end_headers()

    tracking_parameters: str = ""
    validate_url: Pattern[str] = re.compile(r'/sitemap-(\w+)-(\w+).xml')
    tracking_match: Optional[Match[str]] = re.match(validate_url, self.path)

    if tracking_match:
        tracking_parameters: str = "/?utm_source={utm_source}&utm_medium={utm_medium}&utm_campaign=sitemap" \
            .format(utm_source=tracking_match.groups()[0],
                    utm_medium=tracking_match.groups()[1])  # source example (google), medium example (search)

    load_tweets_query: str = '''
        -- 50000
        select id from tweets order by id desc limit 1000
    '''

    urls_dict: dict = self.repo.sql(query=load_tweets_query, result_format="csv")
    urls: pd.DataFrame = pd.DataFrame(urls_dict)

    # Rename ID Column To Loc For XML
    urls.rename(columns={"id": "loc"}, inplace=True)

    # Modify Data For XML
    urls["changefreq"] = "monthly"
    urls["loc"] = config.SITEMAP_PREFIX + urls["loc"] + tracking_parameters

    # Convert DataFrame Back To Dictionary For Conversion To XML
    sitemap_dict: List[dict] = urls.to_dict(orient="records")

    # XML Elements
    urls_xml: Element = dict_to_xml(root_tag='urlset', iter_tag='url', urls=sitemap_dict)

    self.wfile.write(tostring(urls_xml, encoding='utf8', method='xml'))


def load_privacy_page(self):
    # Site Data
    site_title: str = "Privacy Policy"

    # Twitter Metadata
    twitter_title: str = site_title
    twitter_description: str = "Rover's Privacy Policy"

    # HTTP Headers
    self.send_response(200)
    self.send_header("Content-type", "text/html")

    helper_functions.handle_tracking_cookie(self=self)
    helper_functions.send_standard_headers(self=self)
    self.end_headers()

    # Header
    write_header(self=self, site_title=site_title, twitter_title=twitter_title, twitter_description=twitter_description)

    # Lookup User Query
    cookies: Optional[dict] = helper_functions.get_cookies(self=self)
    if cookies is not None and 'analytics' in cookies:
        tracker_id: str = cookies['analytics']
        lookup_user_query: str = urllib.parse.quote_plus(
            f'select * from web where tracker="{tracker_id}" order by date desc;')
    else:
        lookup_user_query: str = urllib.parse.quote_plus(f'select * from web order by date desc;')

    lookup_user_url: str = f"{config.ANALYTICS_REPO_USER_URL}?q={lookup_user_query}"

    # Body
    privacy_page: str = load_text_file(f"rover/server/web/pages/privacy.html") \
        .replace("{analytics_contact_info_type}", config.ANALYTICS_CONTACT_INFO_TYPE) \
        .replace("{analytics_contact_info}", config.ANALYTICS_CONTACT_INFO) \
        .replace("{view_my_info_link}", lookup_user_url)

    self.wfile.write(bytes(privacy_page, "utf-8"))

    # Footer
    write_footer(self=self)
