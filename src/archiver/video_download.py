#!/usr/bin/python

import logging
import os
import threading
import youtube_dl

from config import config as main_config
from doltpy.core.system_helpers import get_logger


class DownloadLogger(object):
    def __init__(self):
        # Logger
        self.logger: logging.Logger = get_logger(__name__)

    def debug(self, msg):
        self.logger.debug(msg=msg)

    def warning(self, msg):
        self.logger.warning(msg=msg)

    def error(self, msg):
        self.logger.error(msg=msg)


class VideoDownloader(threading.Thread):
    def __init__(self, threadID: int, name: str, video_url: str, output_directory: str, callback: classmethod, tweet_id: int):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name

        # Logger
        self.logger: logging.Logger = get_logger(__name__)
        self.INFO_QUIET: int = main_config.INFO_QUIET
        self.VERBOSE: int = main_config.VERBOSE

        # Video URL
        self.video_url: str = video_url

        # Output Directory
        self.output_directory: str = output_directory

        # Callback
        self.callback: classmethod = callback
        self.tweet_id: int = tweet_id

    def run(self):
        self.logger.log(self.INFO_QUIET, f"Starting {self.name} For Video {self.video_url}")
        self.download_video()

    def download_status_hook(self, progress: dict):
        # Downloading: {'status': 'downloading', 'downloaded_bytes': 1526432, 'total_bytes': 1526432, 'tmpfilename': 'Trump supporters love to read-QgVMG4wmJ40.m4a.part', 'filename': 'Trump supporters love to read-QgVMG4wmJ40.m4a', 'eta': 0, 'speed': 11964045.826860763, 'elapsed': 0.21476292610168457, '_eta_str': '00:00', '_percent_str': '100.0%', '_speed_str': '11.41MiB/s', '_total_bytes_str': '1.46MiB'}
        # Downloaded: {'downloaded_bytes': 1526432, 'total_bytes': 1526432, 'filename': 'Trump supporters love to read-QgVMG4wmJ40.m4a', 'status': 'finished', 'elapsed': 0.217087984085083, '_total_bytes_str': '1.46MiB', '_elapsed_str': '00:00'}

        if progress['status'] == 'downloading':
            percent_downloaded: float = (progress['downloaded_bytes']/progress['total_bytes'])*100
            self.logger.info(f'Downloaded {percent_downloaded}% Of "{self.video_url}"...')
        elif progress['status'] == 'finished':
            self.logger.info(f'Done Downloading "{self.video_url}", Now Converting...')

    def download_video(self):
        self.logger.debug(self.output_directory)

        ydl_opts = {
            'logger': DownloadLogger(),
            'progress_hooks': [self.download_status_hook],
            'outtmpl': os.path.join(self.output_directory, "%(title)s.%(ext)s")
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(self.video_url, download=False)
            download_target = os.path.basename(ydl.prepare_filename(info))

            ydl.download([self.video_url])
            self.callback(tweet_id=self.tweet_id, file=download_target)
