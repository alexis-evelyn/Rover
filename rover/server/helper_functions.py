#!/usr/bin/python
import datetime
import random
import uuid
from typing import List, Optional, Tuple


def handle_tracking_cookie(self) -> Optional[Tuple[str, str]]:
    if "DNT" in self.headers and self.headers["DNT"] == "1":
        self.send_header("Set-Cookie", "analytics=honor_dnt;expires=Thu, 01 Jan 1970 00:00:00 GMT,session=honor_dnt;expires=Thu, 01 Jan 1970 00:00:00 GMT")
        return

    expires = datetime.datetime.utcnow() + datetime.timedelta(days=30)  # expires in 30 days
    expire_time: str = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

    uuid_tracking: uuid.UUID = uuid.uuid4()
    uuid_session: str = str(random.sample(range(1, 1000000), 1)[0])

    if "cookie" in self.headers:
        cookies_split: List[str] = self.headers['cookie'].split('; ')
        cookies: dict = {}

        for cookie_split in cookies_split:
            cookie: List[str] = cookie_split.split('=')
            cookies[cookie[0]] = cookie[1]

        if 'analytics' in cookies and 'session' in cookies:
            return cookies['analytics'], cookies['session']
        elif 'analytics' in cookies:
            self.send_header("Set-Cookie", f"session={uuid_session};path=/")
        elif 'session' in cookies:
            self.send_header("Set-Cookie", f"analytics={uuid_tracking};expires={expire_time};path=/")

    self.send_header("Set-Cookie", f"analytics={uuid_tracking};expires={expire_time},session={uuid_session};path=/")
