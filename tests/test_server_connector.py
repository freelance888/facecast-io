import os
from time import sleep

import httpx
import pytest

from facecast_io import ServerConnector, BASE_URL, BASE_HEADERS

TEST_DEVICE_NAME = "TEST_DEVICE_NAME"


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


def test_create_delete_device(server_connector):
    assert server_connector.create_device(TEST_DEVICE_NAME)
    sleep(5)
    devices = [d for d in server_connector.get_devices() if d.name == TEST_DEVICE_NAME]

    assert len(devices) == 1
    device = devices[0]
    assert server_connector.delete_device(device.rtmp_id)
    sleep(5)

    devices = [d for d in server_connector.get_devices() if d.name == TEST_DEVICE_NAME]
    assert len(devices) == 0


def test_create_delete_output(server_connector, rtmp_id):
    result = server_connector.create_output(
        rtmp_id, "rtmp://some.com", "sharedkey", "TEST OUTPUT"
    )
    assert result.ok
    assert len(result.outputs) == 1
    output = result.outputs[0]
    server_connector.delete_output(rtmp_id, output.id)
    outputs = server_connector.get_outputs(rtmp_id)
    assert len(outputs) == 0


def test_server_connector(server_connector, rtmp_id):
    device = server_connector.get_device(rtmp_id)
    status = server_connector.get_status(rtmp_id)
    output = server_connector.get_outputs(rtmp_id)
