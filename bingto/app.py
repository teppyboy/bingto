import argparse
from bingto import __version__
from bingto.constant import EDGE_IOS_UA, WORD_LIST
from playwright.sync_api import (
    sync_playwright,
    Error,
    Page,
    Browser,
    TimeoutError,
    Playwright,
)
from pathlib import Path
from time import sleep
from random import choice, randint, uniform
from runpy import run_module
from undetected_playwright import stealth_sync
import sys


DEBUG = False


def dbg_pause():
    """
    Pause the program if DEBUG is True.
    """
    if DEBUG:
        input("[DEBUG]: Press [ENTER] to continue execution.")


def dbg_screenshot(page: Page, name: str):
    """
    Take a screenshot if DEBUG is True.
    """
    if DEBUG:
        page.screenshot(path=f"{name}.png")


def dbg_print(*args, **kwargs):
    if DEBUG:
        print("[DEBUG]:", *args, **kwargs)


def wait(a: float, b: float):
    """
    Wait for a random amount of time between a and b seconds.
    """
    sleep(uniform(a, b))


def create_browser(p: Playwright, headless: bool) -> Browser:
    try:
        browser = p.chromium.launch(headless=headless, channel="msedge")
    except Error as e:
        print(f"Error occurred while launching Edge: {e}")
        print("Trying to launch Chromium...")
        browser = p.chromium.launch(headless=headless)
    return browser


def login():
    """
    Initiate the login process for Bing.
    """
    print("This will initiate the login process for Bing.")
    print("After logging in, press [ENTER] to continue.", end="")
    with sync_playwright() as p:
        browser = create_browser(p, False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://login.live.com/login.srf")
        input()
        print("Saving browser cookies...")
        try:
            context.storage_state(path="cookies.json")
        except Error as e:
            print(f"Error occurred while saving cookies: {e}")
            exit(1)
        print("Cookies saved to cookies.json")
        print("===========================================")
        print("DO NOT SHARE THE COOKIES FILE WITH ANYONE!")
        print(
            "IT CONTAINS YOUR LOGIN INFORMATION, AND CAN BE USED TO ACCESS YOUR ACCOUNT!"  # noqa: E501
        )
        print("===========================================")
        print("Closing browser...")
        browser.close()


def get_score(page: Page, mobile: bool = False) -> int:
    """
    Get the current score.
    """
    if mobile:
        dbg_print("Mobile mode, opening drawer...")
        page.locator("#mHamburger").click()
        wait(0.5, 1.5)
        for _ in range(3):
            dbg_print("Getting score...")
            try:
                return int(page.locator("#fly_id_rc").inner_text(timeout=1000))
            except ValueError:
                dbg_print("Error occurred while parsing score, waiting...")
                wait(0.5, 1.5)
            except TimeoutError:
                dbg_print("Timeout occurred while parsing score, opening drawer...")
                page.locator("#mHamburger").click()
                wait(0.5, 1.5)
        return -1
    else:
        dbg_print("PC mode.")
        for _ in range(3):
            dbg_print("Getting score...")
            try:
                return int(page.locator("#id_rc").inner_text(timeout=1000))
            except ValueError:
                dbg_print("Error occurred while parsing score, waiting...")
                wait(0.5, 1.5)
        return -1


def search(page: Page, mobile: bool = False):
    print("Initializing word list...")
    print("Starting search...")
    prev_score = -1
    m_same_score = 0
    for i in range(50):
        print(f"Search attempt {i + 1}/30")
        word_len = randint(2, 10)
        print("Word length:", word_len)
        words = []
        for _ in range(word_len):
            words.append(choice(list(WORD_LIST)))
        print("Word:", words)
        generated_query = "+".join(words)
        print("Generated query:", generated_query)
        page.goto(f"https://www.bing.com/search?q={generated_query}&form=QBLH")
        wait(3, 4)
        curr_score = get_score(page, mobile)
        print("Current score:", curr_score)
        print("Previous score:", prev_score)
        if curr_score == -1:
            print("Error occurred while parsing score, skipping...")
            continue
        if curr_score == prev_score:
            if not mobile:
                print("Score did not change, probably we searched enough.")
                break
            else:
                dbg_print("Mobile same score:", m_same_score)
                if m_same_score == 3:
                    print("Score did not change 3 times, probably we searched enough.")
                    break
                m_same_score += 1
        prev_score = curr_score
        dbg_pause()
    print("Search complete.")


def launch_pc(p: Playwright, silent: bool = False, force_chromium: bool = False):
    print("Launching browser (PC version)...")
    if silent or force_chromium:
        browser = p.chromium.launch(headless=silent)
    else:
        browser = create_browser(p, silent)
    print("Loading config & cookies...")
    edge = p.devices["Desktop Edge"]
    context = browser.new_context(**edge, storage_state="cookies.json")
    stealth_sync(context)
    page = context.new_page()
    print("Visiting Bing...")
    page.goto("https://bing.com")
    dbg_screenshot(page, "bing-chromium-1")
    dbg_pause()
    wait(3, 5)
    print("Clicking the 'Login' button...")
    dbg_screenshot(page, "bing-chromium-2")
    page.locator("#id_l").click()
    wait(2, 3)
    print("Executing search function...")
    search(page)
    dbg_pause()
    print("Closing browser...")
    browser.close()


def launch_mobile(p: Playwright, silent: bool = False):
    print("Launching browser (Mobile version)...")
    webkit = p.webkit
    # print(p.devices)
    iphone = p.devices["iPhone 13 Pro Max"]
    print("Monkey-patching WebKit user agent...")
    iphone["user_agent"] = EDGE_IOS_UA
    browser = webkit.launch(headless=silent)
    print("Loading config & cookies...")
    context = browser.new_context(**iphone, storage_state="cookies.json")
    page = context.new_page()
    print("Visiting Bing...")
    page.goto("https://bing.com")
    dbg_screenshot(page, "bing-webkit-1")
    dbg_pause()
    wait(1, 2)
    print("Opening the drawer...")
    dbg_screenshot(page, "bing-webkit-2")
    page.locator("#mHamburger").click()
    wait(1, 2)
    print("Clicking the 'Login' button...")
    page.locator("#hb_s").click()
    wait(1, 2)
    print("Executing search function...")
    search(page, mobile=True)
    dbg_pause()
    print("Closing browser...")
    browser.close()


def install_deps():
    """
    Install required dependencies.
    """
    print("Installing Playwright...")
    sys.argv = ["playwright", "install", "chromium", "webkit"]
    run_module("playwright", run_name="__main__")
    print("Dependencies installed.")


def main():
    global DEBUG
    parser = argparse.ArgumentParser(
        prog="Bingto",
        description="Automate Bing searches to earn Microsoft Rewards points.",  # noqa: E501
        epilog="https://github.com/teppyboy/bingto",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install required dependencies and exit",
        default=False,
    )
    parser.add_argument(
        "--skip-pc",
        action="store_true",
        help="Skip PC version of Bing",
        default=False,
    )
    parser.add_argument(
        "--skip-mobile",
        action="store_true",
        help="Skip mobile version of Bing",
        default=False,
    )
    parser.add_argument(
        "--silent", action="store_true", help="Enable silent mode.", default=False
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode.", default=False
    )
    parser.add_argument(
        "--force-chromium",
        action="store_true",
        help="Force use of Chromium even if Edge is available.",
    )
    args = parser.parse_args()
    DEBUG = args.debug
    print(f"Bingto {__version__} - https://github.com/teppyboy/bingto")
    print("")
    if args.install:
        install_deps()
        exit()
    if not Path("cookies.json").exists():
        print("Cookies file not found.")
        login()
    with sync_playwright() as p:
        # PC
        if not args.skip_pc:
            launch_pc(p, args.silent, args.force_chromium)
        # Mobile
        if not args.skip_mobile:
            launch_mobile(p, args.silent)
