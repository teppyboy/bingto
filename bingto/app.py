import argparse
from english_words import get_english_words_set
from playwright.sync_api import sync_playwright, Error, Page
from pathlib import Path
from time import time, sleep
from random import choice, randint, uniform
from runpy import run_module
import sys


DEBUG = False


def dbg_pause():
    """
    Pause the program if DEBUG is True.
    """
    if DEBUG:
        input("Debug is enabled, press [ENTER] to continue execution.")


def wait(a: float, b: float):
    """
    Wait for a random amount of time between a and b seconds.
    """
    sleep(uniform(a, b))


def login():
    """
    Initiate the login process for Bing.
    """
    print("This will initiate the login process for Bing.")
    print("After logging in, press [ENTER] to continue.", end="")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
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


def search(page: Page):
    print("Initializing word list...")
    start_time = time()
    word_list = get_english_words_set(["web2"], lower=True)
    print(f"Word list initialized in {time() - start_time}s")
    print("Starting search...")
    prev_score = 0
    for i in range(10):
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
        wait(2, 5)
        try:
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
    sys.argv = ["playwright", "install", "chromium"]
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
        browser = p.chromium.launch(headless=args.silent)
        print("Loading cookies...")
        context = browser.new_context(storage_state="cookies.json")
        page = context.new_page()
        print("Visiting Bing...")
        page.goto("https://bing.com")
        wait(3, 5)
        print("Clicking the 'Login' button...")
        page.locator("#id_l").click()
        wait(2, 3)
        print("Executing search function...")
        search(page)
        dbg_pause()
        print("Closing browser...")
        browser.close()
