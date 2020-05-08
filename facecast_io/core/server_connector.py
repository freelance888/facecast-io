import json
import re
from copy import copy
from json import JSONDecodeError
from typing import Dict, List, Literal, cast, Union

import yarl
from httpx import Client
from pyquery import PyQuery as pq  # type:ignore
from retry import retry


from facecast_io.logger_setup import logger
from .entities import (
    DeviceSimple,
    DeviceInput,
    DeviceOutputStatus,
    SelectServerStatus,
    OutputStatus,
    OutputStatusStart,
    DeviceInfo,
    DeviceOutput,
    DeviceStatusFull,
    SelectServer,
)

BASE_URL = "https://b1.facecast.io/"
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


class FacecastAPIError(Exception):
    ...


class AuthError(FacecastAPIError):
    ...


class DeviceNotFound(FacecastAPIError):
    ...


RETRY_TRIES = 3
RETRY_DELAY = 5
RETRY_JITTER = (2, 7)


class ServerConnector:
    def __init__(self, client: Client):
        self.client = client
        self.is_authorized: bool = False
        self.form_sign = None

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

    @retry(
        JSONDecodeError,
        tries=RETRY_TRIES,
        delay=RETRY_DELAY,
        jitter=RETRY_JITTER,
        logger=logger,
    )
    def do_auth(self, username: str, password: str) -> bool:
        r = self.client.get("en/main")
        if r.url == "en/main":
            self.is_authorized = True
            return True
        signature = self._fetch_signature(r.text)
        r = self.client.post(
            "en/login",
            params={"mode": "ajaj"},
            data={"login": username, "pass": password, "signature": signature,},
            headers=AJAX_HEADERS,
        )
        if r.status_code == 200 and r.json().get("ok"):  # type: ignore
            self.is_authorized = True
            self._update_from_sign()
            logger.info("Auth successful")
            return True
        self.is_authorized = False
        raise AuthError("AuthService error")

    def get_devices(self) -> List[DeviceSimple]:
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
        return [
            DeviceSimple(
                rtmp_id=device.attrib["href"].split("=")[1], name=device_name.text,
            )
            for device, device_name in zip(devices, devices_names)
        ]

    @retry(
        JSONDecodeError,
        tries=RETRY_TRIES,
        delay=RETRY_DELAY,
        jitter=RETRY_JITTER,
        logger=logger,
    )
    def get_device(self, rtmp_id: str) -> DeviceInfo:
        r = self.client.post(
            "en/rtmp",
            data={"action": "get_info"},
            params={"rtmp_id": rtmp_id},
            headers=AJAX_HEADERS,
        )
        if r.url.path == "/en/main":
            raise DeviceNotFound(f"{rtmp_id} isn't available")
        data = r.json()
        logger.debug(f"Got device: {data}")
        return cast(DeviceInfo, data)

    @retry(
        JSONDecodeError,
        tries=RETRY_TRIES,
        delay=RETRY_DELAY,
        jitter=RETRY_JITTER,
        logger=logger,
    )
    def create_device(self, name: str) -> bool:
        r = self.client.post(
            "en/main_add/ajaj",
            data={"cmd": "add_rtmp", "sbin": 0, "sign": self.form_sign, "title": name},
        )
        if r.status_code == 200:
            logger.info(f"Device {name} was created")
            return True
        logger.info(f"Device {name} was not created")
        return False

    def delete_device(self, rtmp_id: str) -> bool:
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

    def get_input_params(self, rtmp_id: str) -> DeviceInput:
        r = self.client.get("en/rtmp", params={"rtmp_id": rtmp_id})
        d = pq(r.text)
        server_url = d(".sb-input-input-url").attr["value"]
        if yarl.URL(server_url).host is None:
            return self.get_input_params(rtmp_id)
        shared_key = d(".sb-input-sharedkey").attr["value"]
        di = DeviceInput(rtmp_id=rtmp_id, server_url=server_url, shared_key=shared_key)
        logger.debug(f"DeviceInput {di}")
        return di

    def get_status(self, rtmp_id: str) -> DeviceStatusFull:
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
        data = r.json()
        logger.debug(f"Got device status: {data}")
        return cast(DeviceStatusFull, data)

    @retry(
        JSONDecodeError,
        tries=RETRY_TRIES,
        delay=RETRY_DELAY,
        jitter=RETRY_JITTER,
        logger=logger,
    )
    def get_outputs(self, rtmp_id: str) -> List[DeviceOutput]:
        r = self.client.post(
            "en/rtmp_outputs/ajaj",
            data={"cmd": "getlist", "rtmp_id": rtmp_id, "sign": self.form_sign},
            params={"rtmp_id": rtmp_id},
            headers=AJAX_HEADERS,
        )
        data = r.json()
        logger.debug(f"Got device outputs: {data}")
        return cast(List[DeviceOutput], data)

    @retry(
        JSONDecodeError,
        tries=RETRY_TRIES,
        delay=RETRY_DELAY,
        jitter=RETRY_JITTER,
        logger=logger,
    )
    def update_output(
        self,
        rtmp_id: str,
        output_id: str,
        server_url: str,
        shared_key: str,
        title: str,
        audio: int = 0,
    ) -> DeviceOutput:
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
            },
            headers=AJAX_HEADERS,
        )
        data = r.json()
        logger.debug(f"Updated device output: {data}")
        return cast(DeviceOutput, data)

    @retry(
        JSONDecodeError, tries=RETRY_TRIES + 5, delay=RETRY_DELAY, jitter=RETRY_JITTER
    )
    def create_output(
        self,
        rtmp_id: str,
        server_url: str,
        shared_key: str,
        title: str,
        audio: int = 0,
        stream_type: Literal["rtmp", "mpegts"] = "rtmp",
    ) -> DeviceOutputStatus:
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
            },
            headers=AJAX_HEADERS,
        )
        if r.text == "No auth":
            raise AuthError
        data = r.json()
        logger.debug(f"Updated device output: {data}")
        return cast(DeviceOutputStatus, data)

    @retry(
        JSONDecodeError,
        tries=RETRY_TRIES,
        delay=RETRY_DELAY,
        jitter=RETRY_JITTER,
        logger=logger,
    )
    def delete_output(self, rtmp_id: str, oid: str) -> DeviceOutput:
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
        data = r.json()
        logger.debug(f"Deleted device output: {data}")
        return cast(DeviceOutput, data)

    @retry(
        JSONDecodeError,
        tries=RETRY_TRIES,
        delay=RETRY_DELAY,
        jitter=RETRY_JITTER,
        logger=logger,
    )
    def _output_management(self, rtmp_id: str, oid: str, cmd: str):
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
        return r.json()

    def start_output(self, rtmp_id: str, oid: str) -> OutputStatusStart:
        return cast(OutputStatusStart, self._output_management(rtmp_id, oid, "start"))

    def stop_output(self, rtmp_id: str, oid: str) -> OutputStatus:
        return cast(OutputStatus, self._output_management(rtmp_id, oid, "stop"))

    def get_available_servers(self, rtmp_id: str) -> List[SelectServer]:
        r = self.client.post("en/rtmp_server?mode=", data={"rtmp_id": rtmp_id})
        match = re.search(r"var servers = (\[.*\]);", r.text)
        if match:
            data = json.loads(match.group(1))
            logger.debug(f"Got next servers list {data}")
            return [SelectServer(id=d["id"], name=d["name"]) for d in data]
        raise Exception

    @retry(
        JSONDecodeError,
        tries=RETRY_TRIES,
        delay=RETRY_DELAY,
        jitter=RETRY_JITTER,
        logger=logger,
    )
    def select_server(
        self, rtmp_id: str, server_id: Union[int, str]
    ) -> SelectServerStatus:
        r = self.client.post(
            "en/rtmp",
            data={
                "cmd": "select_server",
                "sign": self.form_sign,
                "rtmp_id": rtmp_id,
                "server_id": server_id,
            },
            params={"rtmp_id": rtmp_id},
            headers=AJAX_HEADERS,
        )
        data = r.json()
        if data["ok"] and data["server"].get("name"):
            logger.info(f"Selected server {data['server']['name']}")
        return cast(SelectServerStatus, r.json())
