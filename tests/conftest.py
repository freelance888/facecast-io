import os
from time import sleep

import httpx
import pytest

from facecast_io import ServerConnector, BASE_URL, BASE_HEADERS

TEST_DEVICE_NAME = "TEST_DEVICE_NAME"


@pytest.fixture
def device_name():
    return TEST_DEVICE_NAME


@pytest.fixture(scope="session")
def client():
    return httpx.Client(base_url=BASE_URL, verify=False, headers=BASE_HEADERS,)


@pytest.fixture(scope="session")
def server_connector(client):
    sc = ServerConnector(client)
    sc.do_auth(os.environ["FACECAST_USERNAME"], os.environ["FACECAST_PASSWORD"])
    return sc


@pytest.fixture
def rtmp_id(server_connector):
    server_connector.create_device(TEST_DEVICE_NAME)
    sleep(5)
    dev = [d for d in server_connector.get_devices() if d.name == TEST_DEVICE_NAME][0]
    yield dev.rtmp_id
    server_connector.delete_device(dev.rtmp_id)
