import re
from copy import copy
from typing import Dict, List, Literal

import yarl
from httpx import Client
from pyquery import PyQuery as pq


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


class AuthError(Exception):
    ...


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
        if r.status_code == 200 and r.json().get("ok"):
            self.is_authorized = True
            self._update_from_sign()
            return True
        self.is_authorized = False
        raise AuthError("AuthService error")

    def get_devices(self) -> List[Dict]:
        r = self.client.get("en/main")
        d = pq(r.text)
        devices = d(".sb-streamboxes-main-list a")
        devices_names = devices.find(".sb-streambox-item-name")
        return [
            dict(rtmp_id=device.attrib["href"].split("=")[1], name=device_name.text,)
            for device, device_name in zip(devices, devices_names)
        ]

    def get_device(self, rtmp_id: str) -> Dict:
        r = self.client.post(
            "en/rtmp",
            data={"action": "get_info"},
            params={"rtmp_id": rtmp_id},
            headers=AJAX_HEADERS,
        )
        return r.json()

    def create_device(self, name: str) -> bool:
        r = self.client.post(
            "en/main_add/ajaj",
            data={"cmd": "add_rtmp", "sbin": 0, "sign": self.form_sign, "title": name},
        )
        return r.status_code == 200

    def delete_device(self, rtmp_id: str) -> bool:
        r = self.client.post(
            "en/rtmp_popup_menu/ajaj",
            data={
                "cmd": "delete_rtmp_source",
                "sign": self.form_sign,
                "rtmp_id": rtmp_id,
            },
        )
        return r.status_code == 200

    def get_input_params(self, rtmp_id: str) -> Dict:
        r = self.client.get("en/rtmp", params={"rtmp_id": rtmp_id})
        d = pq(r.text)
        server_url = d(".sb-input-input-url").attr["value"]
        if yarl.URL(server_url).host is None:
            return self.get_input_params(rtmp_id)
        shared_key = d(".sb-input-sharedkey").attr["value"]
        return dict(server_url=server_url, shared_key=shared_key)

    def get_status(self, rtmp_id: str) -> Dict:
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
        return r.json()

    def get_outputs(self, rtmp_id: str) -> Dict:
        r = self.client.post(
            "en/rtmp_outputs/ajaj",
            data={"cmd": "getlist", "rtmp_id": rtmp_id, "sign": self.form_sign},
            params={"rtmp_id": rtmp_id},
            headers=AJAX_HEADERS,
        )
        return r.json()

    def update_output(
        self,
        rtmp_id: str,
        output_id: str,
        server_url: str,
        shared_key: str,
        title: str,
        audio: int = 0,
    ):
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
        return r.json()

    def create_output(
        self,
        rtmp_id: str,
        server_url: str,
        shared_key: str,
        title: str,
        audio: int = 0,
        stream_type: Literal["rtmp", "mpegts"] = "rtmp",
    ) -> Dict:
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
        return r.json()

    def delete_output(self, rtmp_id: str, oid: str) -> Dict:
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
        return r.json()

    def _output_management(self, oid, cmd):
        r = self.client.post(
            "en/out_rtmp_rtmp/ajaj",
            data={
                "cmd": cmd,
                "sign": self.form_sign,
                "oid": oid,
                "ignore_dirty_buffer": False,
            },
            headers=AJAX_HEADERS,
        )
        return r.json()

    def start_output(self, oid: str) -> Dict:
        return self._output_management(oid, "start")

    def stop_output(self, oid: str) -> Dict:
        return self._output_management(oid, "stop")

    def select_server(self, rtmp_id, server_id):
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
        return r.json()
