import argparse
import logging
import sys
from bingto import __version__
from bingto.constant import VALID_IOS_VERSIONS, EDGE_IOS_UA, WORD_LIST
from playwright.sync_api import (
    sync_playwright,
    Error,
    Page,
    Browser,
    BrowserType,
    TimeoutError,
    Playwright,
)
from pathlib import Path
from time import sleep
from random import choice, randint, uniform
from runpy import run_module

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s (%(funcName)s) (%(filename)s:%(lineno)d) [%(levelname)s]: %(message)s",
)  # noqa: E501


fake_playwright_stealth_init = False


def init_fake_playwright_stealth():
    global fake_playwright_stealth_init
    if fake_playwright_stealth_init:
        return
    fake_playwright_stealth_init = True
    logging.warning("Using dummy implementations for 'playwright_stealth'...")
    logging.warning("Bingto may be easier to be detected, use at your own risk.")
    global stealth_sync

    def stealth_sync(page: Page):
        logging.warning("Dummy function called.")
        pass


try:
    from playwright_stealth import stealth_sync
except ImportError:
    logging.warning("playwright_stealth failed to import.")
    init_fake_playwright_stealth()


DEBUG = False


class Debug:
    @staticmethod
    def pause():
        """
        Pause the program if DEBUG is True.
        """
        if DEBUG:
            logging.debug("Press [ENTER] to continue execution.")
            input()

    @staticmethod
    def screenshot(page: Page, name: str):
        """
        Take a screenshot if DEBUG is True.
        """
        if DEBUG:
            page.screenshot(path=f"{name}.png")

    @staticmethod
    def print(*args, **kwargs):
        """
        logging.info if DEBUG is True.
        """
        if DEBUG:
            logging.debug(*args, **kwargs)


def wait(a: float, b: float):
    """
    Wait for a random amount of time between a and b seconds.
    """
    sleep(uniform(a, b))


def create_browser(
    p: Playwright, headless: bool, browser_type: BrowserType = None
) -> Browser:
    try:
        if browser_type:
            browser = browser_type.launch(headless=headless, channel="msedge")
        else:
            browser = p.chromium.launch(headless=headless, channel="msedge")
    except Error as e:
        logging.info(f"Error occurred while launching Edge: {e}")
        logging.info("Trying to launch Chromium...")
        if browser_type:
            browser = browser_type.launch(headless=headless)
        else:
            browser = p.chromium.launch(headless=headless)
    return browser


def login():
    """
    Initiate the login process for Bing.
    """
    logging.info("This will initiate the login process for Bing.")
    logging.info("After logging in, press [ENTER] to continue.")
    with sync_playwright() as p:
        browser = create_browser(p, False)
        context = browser.new_context()
        page = context.new_page()
        stealth_sync(page=page)
        page.goto("https://login.live.com/login.srf")
        input()
        logging.info("Saving browser cookies...")
        try:
            context.storage_state(path="cookies.json")
        except Error as e:
            logging.info(f"Error occurred while saving cookies: {e}")
            exit(1)
        logging.info("Cookies saved to cookies.json")
        logging.info("===========================================")
        logging.info("DO NOT SHARE THE COOKIES FILE WITH ANYONE!")
        logging.info(
            "IT CONTAINS YOUR LOGIN INFORMATION, AND CAN BE USED TO ACCESS YOUR ACCOUNT!"  # noqa: E501
        )
        logging.info("===========================================")
        logging.info("Closing browser...")
        browser.close()


def get_url(page: Page) -> str:
    """
    Get the current URL.
    """
    return page.evaluate("location.href")


def check_session(page: Page):
    """
    Check if the session has expired.

    This is meant to be called after logging in.
    """
    # https://www.bing.com/secure/Passport.aspx
    # If we got this then we need to re-authenticate again.
    url: str = get_url(page)
    Debug.print(url)
    if "https%3a%2f%2fwww.bing.com%2fsecure%2fPassport.aspx" in url and url.startswith(
        "https://login.live.com/login.srf"
    ):
        logging.error("Session expired, please delete cookies.json and try again.")
        # Exit because we can't do anything else.
        exit(1)


def get_score(page: Page, mobile: bool = False) -> int:
    """
    Get the current score.

    Returns -1 if an error occurred.
    """
    if mobile:
        logging.info("Mobile mode, opening drawer...")
        page.locator("#mHamburger").click()
        wait(0.5, 1.5)
        for _ in range(3):
            logging.info("Getting score...")
            try:
                return int(page.locator("#fly_id_rc").inner_text(timeout=1000))
            except ValueError:
                logging.info("Error occurred while parsing score, waiting...")
                wait(0.5, 1.5)
            except TimeoutError:
                logging.info("Timeout occurred while parsing score, opening drawer...")
                page.locator("#mHamburger").click()
                wait(0.5, 1.5)
        return -1
    else:
        logging.info("PC mode.")
        for _ in range(3):
            logging.info("Getting score...")
            try:
                return int(page.locator("#id_rc").inner_text(timeout=1000))
            except ValueError:
                logging.info("Error occurred while parsing score, waiting...")
                wait(0.5, 1.5)
        return -1


def type_query(page: Page, query: str):
    """
    Simulate typing on Bing.

    Apparently this works for both PC and mobile.
    """
    search_box = page.locator("#sb_form_q")
    search_box.click()
    wait(2, 3)
    search_box.fill(query)
    wait(1, 2)
    page.keyboard.press("Enter")


def search(page: Page, mobile: bool = False):
    prev_score = -1
    same_score_count = 0
    for i in range(50):
        logging.info(f"Search attempt {i + 1}/50")
        word_len = randint(2, 10)
        words = []
        for _ in range(word_len):
            words.append(choice(list(WORD_LIST)))
        logging.info(f"Words: {words} ({word_len})")
        if mobile:
            if i == 0:
                logging.debug("Simulating typing (first search) on mobile...")
                page.locator("#HBleft").click()
                wait(1, 2)
                form_q = page.locator("#sb_form_c")
                form_q.click()
                wait(2, 3)
                page.keyboard.type(" ".join(words), delay=50)
                wait(1, 2)
                page.keyboard.press("Enter")
            else:
                logging.debug("Simulating typing on mobile...")
                try:
                    page.locator("#HBleft").click(timeout=1000)
                except TimeoutError:
                    logging.info("Drawer already closed.")
                type_query(page, " ".join(words))
            wait(2, 3)
            page.locator(".tilk").first.click()
            wait(2, 3)
            page.go_back()
            wait(2, 3)
        else:
            if i == 0:
                # First search is still working, idk how...
                generated_query = "+".join(words)
                page.goto(f"https://www.bing.com/search?q={generated_query}&form=QBLH")
            else:
                logging.debug("Simulating typing on PC...")
                type_query(page, " ".join(words))
        wait(3, 4)
        curr_score = get_score(page, mobile)
        logging.info(f"Score (current / previous): {curr_score} / {prev_score}")
        if curr_score == -1:
            logging.info("Error occurred while parsing score, skipping...")
            continue
        if curr_score == prev_score:
            logging.info(f"Same score count: {same_score_count}")
            if same_score_count == 3:
                logging.info(
                    "Score did not change 3 times, probably we searched enough."
                )
                logging.info(
                    "If the score isn't full, please report this issue on GitHub."
                )
                break
            same_score_count += 1
        prev_score = curr_score
        Debug.pause()
    logging.info("Search complete.")


def launch_pc(p: Playwright, silent: bool = False, force_chromium: bool = False):
    logging.info("Launching browser (PC version)...")
    if silent or force_chromium:
        browser = p.chromium.launch(headless=silent)
    else:
        browser = create_browser(p, silent)
    logging.info("Loading config & cookies...")
    edge = p.devices["Desktop Edge"]
    context = browser.new_context(**edge, storage_state="cookies.json")
    page = context.new_page()
    stealth_sync(page=page)
    logging.info("Visiting Bing...")
    page.goto("https://www.bing.com/")
    Debug.screenshot(page, "bing-chromium-1")
    Debug.pause()
    wait(2, 3)
    logging.info("Clicking the 'Login' button...")
    Debug.screenshot(page, "bing-chromium-2")
    page.locator("#id_l").click()
    Debug.pause()
    wait(1, 2)
    check_session(page)
    logging.info("Executing search function...")
    search(page)
    Debug.pause()
    logging.info("Saving browser cookies...")
    try:
        context.storage_state(path="cookies.json")
    except Error:
        logging.exception("Error occurred while saving new cookies")
        logging.warning("This may cause issues in the future.")
    logging.info("Closing browser...")
    browser.close()


def start_mobile(page: Page):
    stealth_sync(page=page)
    logging.info("Visiting Bing...")
    page.goto("https://www.bing.com/")
    Debug.screenshot(page, "bing-webkit-1")
    Debug.pause()
    wait(1, 2)
    if get_score(page, mobile=True) == -1:
        logging.info("Clicking the 'Login' button...")
        try:
            page.locator("#hb_s").click(timeout=1000)
        except TimeoutError:
            logging.exception("Failed to click the 'Login' button, assuming we're logged in.")  # noqa: E501
    wait(3, 5)
    check_session(page)
    logging.info("Executing search function...")
    search(page, mobile=True)
    Debug.pause()


def launch_mobile(
    p: Playwright,
    silent: bool = False,
    no_webkit: bool = False,
    force_chromium: bool = False,
    real_viewport: bool = False,
    use_pc_profile: bool = False,
):
    logging.info("Launching browser (1) (Mobile version)...")
    if no_webkit:
        browser = p.chromium
    else:
        browser = p.webkit
    logging.debug(p.devices)
    if use_pc_profile:
        iphone = p.devices["Desktop Edge"]
    else:
        iphone = p.devices["iPhone 13 Pro Max"]
    user_agent = EDGE_IOS_UA.format(IOS_VERSION=choice(VALID_IOS_VERSIONS).replace(".", "_"))  # noqa: E501
    logging.info(f"Crafted UA: {user_agent}")
    logging.info("Monkey-patching WebKit user agent...")
    iphone["user_agent"] = user_agent
    if no_webkit and not force_chromium:
        browser = create_browser(p, headless=silent, browser_type=browser)
    else:
        browser = browser.launch(headless=silent)
    logging.info("Loading config & cookies...")
    context = browser.new_context(**iphone, storage_state="cookies.json")
    page = context.new_page()
    if real_viewport:
        iphone = p.devices["iPhone 13 Pro Max"]
        width = iphone["viewport"]["width"] * iphone["device_scale_factor"]
        height = iphone["viewport"]["height"] * iphone["device_scale_factor"]
        page.set_viewport_size({"width": width, "height": height})
    start_mobile(page)
    logging.info("Saving browser cookies...")
    try:
        context.storage_state(path="cookies.json")
    except Error:
        logging.exception("Error occurred while saving new cookies")
        logging.warning("This may cause issues in the future.")
    logging.info("Closing browser...")
    browser.close()


def install_deps():
    """
    Install required dependencies.
    """
    logging.info("Installing Playwright dependencies...")
    sys.argv = ["playwright", "install", "chromium", "webkit"]
    run_module("playwright", run_name="__main__")
    logging.info("Dependencies installed.")


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
        "--no-webkit",
        action="store_true",
        help="Do not use WebKit for mobile emulation.",
    )
    parser.add_argument(
        "--force-chromium",
        action="store_true",
        help="Force use of Chromium even if Edge is available.",
    )
    parser.add_argument(
        "--no-stealth",
        action="store_true",
        help="Do not use playwright_stealth.",
    )
    # Mobile-only args
    parser.add_argument(
        "--m-real-viewport",
        action="store_true",
        help="Emulate real viewport size (Mobile only).",
    )
    parser.add_argument(
        "--m-use-pc-profile",
        action="store_true",
        help="Uses PC profile instead of phone as a base (Mobile only).",
    )    
    args = parser.parse_args()
    DEBUG = args.debug
    if DEBUG:
        logging.getLogger().setLevel(logging.DEBUG)
    logging.info(f"Bingto {__version__} - https://github.com/teppyboy/bingto")
    if args.install:
        install_deps()
        exit()
    if args.no_stealth:
        init_fake_playwright_stealth()
    if not Path("cookies.json").exists():
        logging.info("Cookies file not found.")
        login()
    with sync_playwright() as p:
        # PC
        if not args.skip_pc:
            launch_pc(p, args.silent, args.force_chromium)
        # Mobile
        if not args.skip_mobile:
            launch_mobile(
                p, args.silent, args.no_webkit, args.force_chromium, args.m_real_viewport, args.m_use_pc_profile
            )
