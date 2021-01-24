#!/usr/bin/python
import uuid
from typing import List, Optional


def handle_tracking_cookie(self) -> Optional[str]:
    if "DNT" in self.headers and self.headers["DNT"] == "1":
        self.send_header("Set-Cookie", "analytics=honor_dnt;expires=Thu, 01 Jan 1970 00:00:00 GMT")
        return

    if "cookie" in self.headers:
        cookies_split: List[str] = self.headers['cookie'].split('; ')
        cookies: dict = {}

        for cookie_split in cookies_split:
            cookie: List[str] = cookie_split.split('=')
            cookies[cookie[0]] = cookie[1]

        if 'analytics' in cookies:
            return cookies['analytics']

    uuid_str: uuid.UUID = uuid.uuid1()
    self.send_header("Set-Cookie", f"analytics={uuid_str}")
