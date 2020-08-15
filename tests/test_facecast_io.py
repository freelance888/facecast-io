import os
from time import sleep

import pytest

from facecast_io import __version__, FacecastAPI


def test_version():
    assert __version__ == "0.5.0"


@pytest.fixture
def api():
    return FacecastAPI(os.environ["FACECAST_USERNAME"], os.environ["FACECAST_PASSWORD"])


def test_devices_crud_operations(api):
    devices = api.devices
    d1 = devices.create_device("TEST_NAME")
    d2 = api.devices["TEST_NAME"]
    assert d1 is d2

    d1 = api.get_or_create_device("TEST_NAME")
    assert d1 is d2

    # TODO: add signals mechanism for backpropagation changes
    # prev_len = len(api.devices)
    # assert api.devices["TEST_NAME"].delete()
    # assert len(api.devices) == prev_len - 1
    prev_len = len(api.devices)
    api.devices.delete_device("TEST_NAME")
    assert len(api.devices) == prev_len - 1


def test_device_operations(api, rtmp_id, device_name):
    assert api.devices.get_device(device_name) is api.devices[rtmp_id]
    assert api.devices.get_device(rtmp_id) is api.devices[device_name]

    str(api.devices)

    device = api.devices[rtmp_id]
    device.start_outputs()
    device.stop_outputs()
    assert device.input_params
