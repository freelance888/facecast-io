from __future__ import absolute_import

import functools
from typing import List, Optional

import httpx

from facecast_io.server_connector import (
    ServerConnector,
    BASE_URL,
    BASE_HEADERS,
)


class APIError(Exception):
    ...


def auth_required(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.is_authorized:
            raise APIError("Need to authorize first")
        return func(self, *args, **kwargs)

    return wrapper


class FacecastAPI:
    def __init__(self, auth: Optional[tuple] = None):
        self.client = httpx.Client(
            base_url=BASE_URL, verify=False, headers=BASE_HEADERS,
        )
        self.server_connector = ServerConnector(self.client)
        if auth:
            self.do_auth(auth[0], auth[1])

    @property
    def is_authorized(self):
        return self.server_connector.is_authorized

    def do_auth(self, username, password):
        return self.server_connector.do_auth(username, password)

    @auth_required
    def get_devices(self) -> List:
        return self.server_connector.get_devices()

    def create_new_device(self, name):
        ...
