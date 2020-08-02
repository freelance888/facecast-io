#!/usr/bin/env python3
import fileinput
import logging
import os
from typing import List
from argparse import ArgumentParser

from pydantic import BaseModel

from facecast_io import FacecastAPI


class Stream(BaseModel):
    channel_name: str
    server_url: str
    stream_key: str
    post_urls: List[str]


class ChannelStream(BaseModel):
    __root__: List[Stream]

    def __iter__(self):
        yield from self.__root__


if __name__ == "__main__":
    parser = ArgumentParser()
    # parser.add_argument("--login", help="Login to facecast")
    parser.add_argument("-d", "--device-name", help="Device name")
    parser.add_argument(
        "files",
        metavar="FILE",
        nargs="*",
        help="files to read, if empty, stdin is used",
    )
    args = parser.parse_args()

    # If you would call fileinput.input() without files it would try to process all arguments.
    # We pass '-' as only file when argparse got no files which will cause fileinput to read from stdin
    text = ""
    for line in fileinput.input(files=args.files if len(args.files) > 0 else ("-",)):
        text += line

    logging.debug(f"Got next data {text}")
    streams_data = ChannelStream.parse_raw(text)
    api = FacecastAPI(os.environ["FACECAST_USERNAME"], os.environ["FACECAST_PASSWORD"])
    logging.info(f"Next devices are present: {api.get_devices()}")
    api.get_or_create_device(args.device_name)
