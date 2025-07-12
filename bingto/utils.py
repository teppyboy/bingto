from random import uniform
from time import sleep
import logging
from patchright.sync_api import Page
import requests


class Debugger:
    enabled: bool = False
    enable_pause: bool = False

    @staticmethod
    def pause():
        """
        Pause the program if DEBUG is True.
        """
        if Debugger.enabled and Debugger.enable_pause:
            logging.debug("Press [ENTER] to continue execution.")
            input()

    @staticmethod
    def screenshot(page: Page, name: str):
        """
        Take a screenshot if DEBUG is True.
        """
        if Debugger.enabled:
            page.screenshot(path=f"{name}.png")

    @staticmethod
    def print(*args, **kwargs):
        """
        logging.info if DEBUG is True.
        """
        if Debugger.enabled:
            logging.debug(*args, **kwargs)


def wait(a: float, b: float):
    """
    Wait for a random amount of time between a and b seconds.
    """
    sleep(uniform(a, b))


def get_mobile_edge_version() -> str:
    rsp = requests.get("https://edgeupdates.microsoft.com/api/products")
    rsp.raise_for_status()
    data = rsp.json()
    for release in data[0]["Releases"]:
        if release["Platform"] == "iOS":
            return release["ProductVersion"]
    raise ValueError("No iOS version found.")
