import os

from facecast_io import __version__, FacecastAPI


def test_version():
    assert __version__ == "0.1.2"


def test_facecast_api():
    api = FacecastAPI(
        auth=(os.environ["FACECAST_USERNAME"], os.environ["FACECAST_PASSWORD"])
    )
    api.get_devices()
