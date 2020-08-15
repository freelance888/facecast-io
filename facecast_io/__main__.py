#!/usr/bin/env python3
import fileinput
import os
from getpass import getpass
from pathlib import Path
from typing import List

import typer
from pydantic import BaseModel, BaseSettings, EmailStr
from tld import get_tld
from tld.exceptions import TldBadUrl

from facecast_io import FacecastAPI
from facecast_io.errors import DeviceNotFound


class Stream(BaseModel):
    channel_name: str
    server_url: str
    stream_key: str
    post_urls: List[str]

    def __str__(self):
        return f"{short_output(self.server_url)} - {self.channel_name}"


class ChannelStream(BaseModel):
    __root__: List[Stream]

    def __iter__(self) -> List[Stream]:
        yield from self.__root__


class Config(BaseSettings):
    facecast_username: str
    facecast_password: str


def bctext(text):
    return typer.style(text, fg=typer.colors.BRIGHT_CYAN, bold=True)


def rtext(text):
    return typer.style(text, fg=typer.colors.RED, bold=True)


def btext(text):
    return typer.style(text, fg=typer.colors.BLUE, bold=True)


def gtext(text):
    return typer.style(text, fg=typer.colors.GREEN, bold=True)


def short_output(url) -> str:
    pattern = {
        "facebook": "FB",
        "vk": "VK",
        "youtube": "YT",
        "ok": "OK",
    }
    try:
        domain = get_tld(url, as_object=True).domain
    except TldBadUrl:
        return ""
    return pattern.get(domain, "")


def get_device_outputs(device):
    live_txt = typer.style("Live", fg=typer.colors.GREEN, bold=True)
    offline_txt = typer.style("Offline", fg=typer.colors.RED, bold=True)
    result = ""
    for i, o in enumerate(device.outputs):
        out = o.output
        conn_text = offline_txt
        if out.enabled:
            if out.cloud:
                conn_text = live_txt
            else:
                conn_text = rtext("Connection issues. Check correctness of stream url")
        result += f"\n\t\t{i}. {short_output(out.server_url)} {typer.style(out.title, bold=True)} - {conn_text}"
    return result if result else "No outputs"


def display_device_status(device):
    name_txt = bctext(device.name)
    live_txt = typer.style("Live", fg=typer.colors.GREEN, bold=True)
    offline_txt = typer.style("Offline", fg=typer.colors.RED, bold=True)
    outputs_text = get_device_outputs(device)
    text = (
        f"Device: {name_txt}"
        f"\n\tInput signal status: {live_txt if device.is_online else offline_txt}"
        f"\n\tOutput status: {outputs_text}"
    )
    typer.echo(text)


def display_device_input(device):
    text = (
        f"Device: {bctext(device.name)}"
        f"\n\tMain: {btext(device.main_server_url)}"
        f"\n\tBackup: {btext(device.backup_server_url)}"
        f"\n\tShared key: {rtext(device.shared_key)}"
    )
    typer.echo(text)


app = typer.Typer()
devices_app = typer.Typer()
app.add_typer(devices_app, name="devices")

api = FacecastAPI()


class FacecastLogin(BaseModel):
    username: EmailStr
    password: str


def _login(force=False):
    config_path = Path().home() / ".facecast.json"
    if config_path.exists() and not force:
        config = FacecastLogin.parse_file(config_path)
    else:
        config = FacecastLogin(
            username=input("Username: "), password=getpass("Password: ")
        )
        with open(config_path, "w") as f:
            f.write(config.json())

    api.do_auth(config.username, config.password)


@app.command()
def login(force: bool = typer.Option(False)):
    _login(force)
    typer.echo(gtext(f"Authorized: {api.is_authorized}"))


@app.command()
def logout():
    config_path = Path().home() / ".facecast.json"
    if config_path.exists():
        os.remove(config_path)
    typer.echo("Logout successfully")


@app.command()
def device(
    name,
    start: bool = typer.Option(False),
    stop: bool = typer.Option(False),
    input: bool = typer.Option(False),
):
    _login()

    name_txt = bctext(name)
    try:
        device = api.devices[name]
    except DeviceNotFound:
        typer.echo(rtext(f"Device not found"))
        return
    if start:
        if device.start_outputs():
            typer.echo(f"Streams started for device: {name_txt}")
            display_device_status(device)
    elif stop:
        device.stop_outputs()
        typer.echo(f"Streams stopped for device: {name_txt}")
        display_device_status(device)
    elif input:
        display_device_input(device)
    else:
        display_device_status(device)


@devices_app.command("list")
def list():
    _login()
    result = ""
    for i, device in enumerate(api.devices):
        result += f"\t{i}. {bctext(device.name)}\n"
    typer.echo(f"Devices: \n{result}")


@devices_app.command("create")
def create(name: str):
    _login()
    device = api.devices.create_device(name)
    typer.echo(f"Device created: {bctext(device.name)} - {device.outputs}")
    display_device_input(device)


@devices_app.command("delete")
def delete(name: str):
    _login()

    typer.confirm(f"Are you sure to delete `{bctext(name)}`?", abort=True)
    for n in name.split(" "):
        status = api.devices.delete_device(n)
        if status:
            typer.echo(f"Device {bctext(n)} deleted")


@devices_app.command("provision")
def provision(lang_code: str,):
    text = ""
    for line in fileinput.input("-"):
        text += line
    if not text:
        typer.echo(rtext("No any input data"))
        return
    streams_data = ChannelStream.parse_raw(text)

    _login()
    device = api.get_or_create_device(lang_code)
    if not streams_data:
        typer.echo(rtext("No input data"))
        return

    if device.outputs:
        typer.confirm("Are you sure you want to continue?", abort=True)

    for stream in streams_data:
        device.create_output(
            name=stream.channel_name,
            server_url=stream.server_url,
            shared_key=stream.stream_key,
        )
        typer.echo(gtext(f"Added {stream}"))


if __name__ == "__main__":
    app()
