import re
from copy import copy
from json import JSONDecodeError

from typing import Union

import httpx
from pydantic import ValidationError

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal  # type:ignore

from httpx import Client
from pyquery import PyQuery as pq  # type:ignore
from retry import retry  # type: ignore


from facecast_io.logger_setup import logger
from .entities import (
    DeviceOutput,
    DeviceOutputs,
    DeviceOutputStatus,
    OutputStatus,
    OutputStatusStart,
    BaseResponse,
    BaseDevice,
    BaseDevices,
    DeviceInfo,
    DeviceStatusFull,
    AvailableServers,
)
from .errors import (
    AuthError,
    DeviceNotFound,
    DeviceNotCreated,
    FacecastAPIError,
)

BASE_URL = "https://b1.facecast.io/"
POSSIBLE_BASE_URLS = [
    "https://b1.facecast.io/",
    "https://b2.facecast.io/",
    "https://b3.facecast.io/",
]

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:28.0) Gecko/20100101 Firefox/28.0",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
}
AJAX_HEADERS = copy(BASE_HEADERS)
AJAX_HEADERS.update(
    {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "x-requested-with": "XMLHttpRequest",
    }
)


RETRY_PARAMS = dict(tries=3, delay=5, jitter=(2, 7), logger=logger)


class ServerConnector:
    def __init__(self, client: Client):
        self.client = client
        self.is_authorized: bool = False
        self.form_sign = None

    def __repr__(self):
        return f"ServerConnector<{self.form_sign}>"

    def _update_from_sign(self):
        r = self.client.get("en/main")
        match = re.search(r"form_sign: \'(\w+)\'", r.text)
        if match:
            self.form_sign = match.group(1)
            return
        raise AuthError("Failed to fetch form_sign")

    def _fetch_signature(self, text):
        match = re.search(r"signature: \'(\w+)\'", text)
        if match:
            return match.group(1)
        raise AuthError("Failed to fetch signature")

    def _check_auth(self):
        if not self.is_authorized:
            raise FacecastAPIError("Need to authorize first")

    @retry(httpx.HTTPError, **RETRY_PARAMS)
    def do_auth(self, username: str, password: str) -> bool:
        r = self.client.get("en/main")
        if r.url == "en/main":
            self.is_authorized = True
            return True
        signature = self._fetch_signature(r.text)
        r = self.client.post(
            "en/login",
            params={"mode": "ajaj"},
            data={"login": username, "pass": password, "signature": signature},
            headers=AJAX_HEADERS,
        )
        if r.status_code == 200 and r.json().get("ok"):  # type: ignore
            self.is_authorized = True
            self._update_from_sign()
            logger.info("Auth successful")
            return True
        self.is_authorized = False
        raise AuthError("AuthService error")

    @retry(httpx.HTTPError, **RETRY_PARAMS)
    def get_devices(self) -> BaseDevices:
        self._check_auth()
        r = self.client.get("en/main")
        d = pq(r.text)
        devices = d(".sb-streamboxes-main-list a")
        devices_names = devices.find(".sb-streambox-item-name")
        if devices_names:
            logger.info(
                f"Got devices with following names: {[d.text for d in devices_names]}"
            )
        else:
            logger.info("No devices")
        return BaseDevices.parse_obj(
            BaseDevice(
                rtmp_id=device.attrib["href"].split("=")[1], name=device_name.text,
            )
            for device, device_name in zip(devices, devices_names)
        )

    @retry(httpx.HTTPError, **RETRY_PARAMS)
    def get_device(self, rtmp_id: int) -> DeviceInfo:
        self._check_auth()
        r = self.client.post(
            "en/rtmp",
            data={"action": "get_info"},
            params={"rtmp_id": rtmp_id},
            headers=AJAX_HEADERS,
        )
        if r.url and r.url.path == "/en/main":
            raise DeviceNotFound(f"{rtmp_id} isn't available")
        data = DeviceInfo.parse_raw(r.content)
        logger.debug(f"Got device: {data}")
        return data

    @retry((httpx.HTTPError, DeviceNotCreated), **RETRY_PARAMS)
    def create_device(self, name: str, stream_type: Literal["rtmp"] = "rtmp") -> bool:
        self._check_auth()
        r = self.client.post(
            "en/main_add/ajaj",
            data={
                "cmd": "add_restreamer",
                "sbin": 0,
                "sign": self.form_sign,
                "type": stream_type,
                "title": name,
            },
        )
        data = BaseResponse.parse_raw(r.content)
        if not data.ok:
            raise DeviceNotCreated(f"{name} wasn't created")

        if r.status_code == 200:
            logger.info(f"Device {name} was created")
            return True
        logger.info(f"Device {name} was not created")
        return False

    @retry(httpx.HTTPError, **RETRY_PARAMS)
    def delete_device(self, rtmp_id: int) -> bool:
        self._check_auth()
        r = self.client.post(
            "en/rtmp_popup_menu/ajaj",
            data={
                "cmd": "delete_rtmp_source",
                "sign": self.form_sign,
                "rtmp_id": rtmp_id,
            },
        )
        if r.status_code == 200:
            logger.info(f"Device {rtmp_id} was deleted")
            return True
        logger.info(f"Device {rtmp_id} was not deleted")
        return False

    @retry(httpx.HTTPError, **RETRY_PARAMS)
    def get_status(self, rtmp_id: int) -> DeviceStatusFull:
        self._check_auth()
        r = self.client.post(
            "en/rtmp/ajaj",
            data={
                "sign": self.form_sign,
                "requests[0][cmd]": "get_status",
                "requests[0][sign]": self.form_sign,
                "requests[1][cmd]": "input_status",
                "requests[1][sign]": self.form_sign,
                "requests[2][cmd]": "output_status",
                "requests[2][sign]": self.form_sign,
                "rtmp_id": rtmp_id,
            },
            params={"rtmp_id": rtmp_id},
            headers=AJAX_HEADERS,
        )
        data = DeviceStatusFull.parse_raw(r.content)
        logger.debug(f"Got device status: {data}")
        return data

    @retry((httpx.HTTPError, FacecastAPIError, ValidationError), **RETRY_PARAMS)
    def get_outputs(self, rtmp_id: int) -> DeviceOutputs:
        self._check_auth()
        r = self.client.post(
            "en/rtmp_outputs/ajaj",
            data={"cmd": "getlist", "rtmp_id": rtmp_id, "sign": self.form_sign},
            params={"rtmp_id": rtmp_id},
            headers=AJAX_HEADERS,
        )
        data = DeviceOutputs.parse_raw(r.content)
        logger.debug(f"Got device outputs: {data}")
        return data

    @retry((httpx.HTTPError, FacecastAPIError), **RETRY_PARAMS)
    def update_output(
        self,
        rtmp_id: str,
        output_id: str,
        server_url: str,
        shared_key: str,
        title: str,
        audio: int = 0,
    ) -> DeviceOutput:
        self._check_auth()
        r = self.client.post(
            "en/out_rtmp_rtmp/ajaj",
            data={
                "cmd": "update",
                "rtmp_id": rtmp_id,
                "oid": output_id,
                "sign": self.form_sign,
                "server_url": server_url,
                "shared_key": shared_key,
                "title": title,
                "audio": audio,
                "server": "auto",
            },
            headers=AJAX_HEADERS,
        )
        data = DeviceOutput.parse_raw(r.content)
        logger.debug(f"Updated device output: {data}")
        return data

    @retry((httpx.HTTPError, FacecastAPIError), **RETRY_PARAMS)
    def create_output(
        self,
        rtmp_id: int,
        server_url: str,
        shared_key: str,
        title: str,
        audio: int = 0,
        stream_type: Literal["rtmp", "mpegts"] = "rtmp",
    ) -> DeviceOutputStatus:
        self._check_auth()
        r = self.client.post(
            "en/out_rtmp_rtmp/ajaj",
            data={
                "cmd": "add",
                "rtmp_id": rtmp_id,
                "oid": 0,
                "sign": self.form_sign,
                "server_url": server_url,
                "shared_key": shared_key,
                "descr": title,
                "type": stream_type,
                "audio": audio,
                "server": "auto",
            },
            headers=AJAX_HEADERS,
        )
        if r.text == "No auth":
            raise AuthError
        data = DeviceOutputStatus.parse_raw(r.content)
        logger.debug(f"Updated device output: {data}")
        return data

    @retry((httpx.HTTPError, FacecastAPIError), **RETRY_PARAMS)
    def delete_output(self, rtmp_id: int, oid: int) -> DeviceOutputStatus:
        self._check_auth()
        r = self.client.post(
            "en/out_rtmp_rtmp/ajaj",
            data={
                "cmd": "delete",
                "sign": self.form_sign,
                "oid": oid,
                "rtmp_id": rtmp_id,
            },
            headers=AJAX_HEADERS,
        )
        data = DeviceOutputStatus.parse_raw(r.content)
        logger.debug(f"Deleted device output: {data}")
        return data

    @retry((httpx.HTTPError, FacecastAPIError), **RETRY_PARAMS)
    def _output_management(self, rtmp_id: int, oid: int, cmd: str):
        self._check_auth()
        r = self.client.post(
            "en/out_rtmp_rtmp/ajaj",
            data={
                "cmd": cmd,
                "rtmp_id": rtmp_id,
                "sign": self.form_sign,
                "oid": oid,
                "ignore_dirty_buffer": False,
            },
            headers=AJAX_HEADERS,
        )
        return r.content

    def start_output(self, rtmp_id: int, oid: int) -> OutputStatusStart:
        return OutputStatusStart.parse_raw(
            self._output_management(rtmp_id, oid, "start")
        )

    def stop_output(self, rtmp_id: int, oid: int) -> OutputStatus:
        return OutputStatus.parse_raw(self._output_management(rtmp_id, oid, "stop"))

    @retry((httpx.HTTPError, FacecastAPIError), **RETRY_PARAMS)
    def get_available_servers(self, rtmp_id: int) -> AvailableServers:
        self._check_auth()
        r = self.client.post("en/rtmp_server?mode=", data={"rtmp_id": rtmp_id})
        match = re.search(r"var servers = '(\[.*\])';", r.text)
        if match:
            data = AvailableServers.parse_raw(match.group(1))
            logger.debug(f"Got next servers list {data}")
            return data
        raise FacecastAPIError("Failed to get available servers")

    @retry((httpx.HTTPError, FacecastAPIError), **RETRY_PARAMS)
    def select_server(self, rtmp_id: int, server_id: int) -> bool:
        self._check_auth()
        r = self.client.post(
            "en/rtmp_server/ajaj",
            data={
                "cmd": "set_server",
                "sign": self.form_sign,
                "rtmp_id": rtmp_id,
                "server_id": server_id,
            },
            params={"rtmp_id": rtmp_id},
            headers=AJAX_HEADERS,
        )
        data = BaseResponse.parse_raw(r.content)
        if data.ok:
            logger.info(f"Server {server_id} selected for {rtmp_id}")
            return True
        raise FacecastAPIError(f"Failed to select server {rtmp_id} - {data}")
