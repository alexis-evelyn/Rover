#!/usr/bin/python
import datetime
import random
import uuid
from typing import List, Optional, Tuple

from rover import config


def handle_tracking_cookie(self) -> Optional[Tuple[str, str]]:
    if "DNT" in self.headers and self.headers["DNT"] == "1":
        self.send_header("Set-Cookie", "analytics=honor_dnt;expires=Thu, 01 Jan 1970 00:00:00 GMT,session=honor_dnt;expires=Thu, 01 Jan 1970 00:00:00 GMT")
        return

    expires = datetime.datetime.utcnow() + datetime.timedelta(days=30)  # expires in 30 days
    expire_time: str = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

    uuid_tracking: uuid.UUID = uuid.uuid4()
    uuid_session: str = str(random.sample(range(1, 1000000), 1)[0])

    # For If Debugging Via Localhost
    _, ip_source = get_ip_address(self=self)
    secure: str = " Secure;" if ip_source != "Direct" else ""

    cookies: Optional[dict] = get_cookies(self=self)
    if cookies is not None:
        if 'analytics' in cookies and 'session' in cookies:
            return cookies['analytics'], cookies['session']
        elif 'analytics' in cookies:
            self.send_header("Set-Cookie", f"session={uuid_session};path=/; HttpOnly;{secure} SameSite=None")
            return None
        elif 'session' in cookies:
            self.send_header("Set-Cookie", f"analytics={uuid_tracking};expires={expire_time};path=/; HttpOnly;{secure} SameSite=None")
            return None

    self.send_header("Set-Cookie", f"analytics={uuid_tracking};expires={expire_time},session={uuid_session};path=/; HttpOnly;{secure} SameSite=None")


def get_cookies(self) -> Optional[dict]:
    if "cookie" in self.headers:
        cookies_split: List[str] = self.headers['cookie'].split('; ')
        cookies: dict = {}

        for cookie_split in cookies_split:
            cookie: List[str] = cookie_split.split('=')
            cookies[cookie[0]] = cookie[1]

        return cookies
    return None


def get_ip_address(self) -> Tuple[str, str]:
    # Cloudflare Forwarded IP
    if 'CF-Connecting-IP' in self.headers:
        ip_address: str = self.headers["CF-Connecting-IP"]
        ip_source: str = "Cloudflare"
    # NGinx Forwarded IP
    elif 'X-Real-IP' in self.headers:
        ip_address: str = self.headers["X-Real-IP"]
        ip_source: str = "NGinx"
    # Direct IP Connecting To This Server
    else:
        ip_address: str = str(self.client_address[0])
        ip_source: str = "Direct"

    return ip_address, ip_source


def send_standard_headers(self):
    # Performance Headers
    if "Service-Worker-Navigation-Preload" in self.headers:
        self.send_header("Vary", "Service-Worker-Navigation-Preload")

    # Security Headers
    self.send_header("X-Content-Type-Options", "nosniff")
    self.send_header("X-XSS-Protection", "1; mode=block")
    self.send_header("X-Frame-Options", "DENY")

    # TODO: Add CONTENT-SECURITY-POLICY and CONTENT-SECURITY-POLICY-REPORT-ONLY From https://www.immuniweb.com/websec/?id=gkh5CGKh
    # self.send_header("CONTENT-SECURITY-POLICY", "...")
    # self.send_header("CONTENT-SECURITY-POLICY-REPORT-ONLY", "...")

    if config.ALLOW_CORS:
        self.send_header("Access-Control-Allow-Origin", config.CORS_SITES)

    if config.ENABLE_HSTS:
        self.send_header("Strict-Transport-Security", config.HSTS_SETTINGS)
