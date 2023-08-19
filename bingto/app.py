import argparse
from bingto.constant import EDGE_IOS_UA
from english_words import get_english_words_set
from playwright.sync_api import sync_playwright, Error, Page, Browser
from pathlib import Path
from time import time, sleep
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
        input("Debug is enabled, press [ENTER] to continue execution.")


def dbg_screenshot(page: Page, name: str):
    """
    Take a screenshot if DEBUG is True.
    """
    if DEBUG:
        page.screenshot(path=f"{name}.png")


def wait(a: float, b: float):
    """
    Wait for a random amount of time between a and b seconds.
    """
    sleep(uniform(a, b))


def create_browser(p: Page, headless: bool) -> Browser:
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


def search(page: Page, mobile: bool = False):
    print("Initializing word list...")
    start_time = time()
    word_list = get_english_words_set(["web2"], lower=True)
    print(f"Word list initialized in {time() - start_time}s")
    print("Starting search...")
    prev_score = -1
    for i in range(36):
        print(f"Search attempt {i + 1}/30")
        word_len = randint(2, 10)
        print("Word length:", word_len)
        words = []
        for _ in range(word_len):
            words.append(choice(list(word_list)))
        print("Word:", words)
        generated_query = "+".join(words)
        print("Generated query:", generated_query)
        page.goto(f"https://www.bing.com/search?q={generated_query}")
        wait(1, 3)
        try:
            if mobile:
                print("Opening the drawer...")
                page.locator("#mHamburger").click()
                wait(0.5, 1.5)
                curr_score = int(page.locator("#fly_id_rc").inner_text())
            else:
                curr_score = int(page.locator("#id_rc").inner_text())
            if curr_score == prev_score:
                print("Score did not change, probably we searched enough.")
                break
            prev_score = curr_score
        except ValueError:
            print("Error occurred while parsing score.")
            continue
    print("Search complete.")


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
    args = parser.parse_args()
    DEBUG = args.debug
    print("Bingto v0.1.0 - https://github.com/teppyboy/bingto")
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
            print("Launching browser (PC version)...")
            if args.silent:
                browser = p.chromium.launch(headless=args.silent)
            else:
                browser = create_browser(p, args.silent)
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
        # Mobile
        if not args.skip_mobile:
            print("Launching browser (Mobile version)...")
            webkit = p.webkit
            # print(p.devices)
            iphone = p.devices["iPhone 13 Pro Max"]
            print("Monkey-patching WebKit user agent...")
            iphone["user_agent"] = EDGE_IOS_UA
            browser = webkit.launch(headless=args.silent)
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
