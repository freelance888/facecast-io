import os

from facecast_io import __version__, FacecastAPI


def test_version():
    assert __version__ == "0.3.1"


def test_facecast_api():
    api = FacecastAPI(os.environ["FACECAST_USERNAME"], os.environ["FACECAST_PASSWORD"])
    api.get_devices()
