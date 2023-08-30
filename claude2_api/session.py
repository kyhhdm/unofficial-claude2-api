import os
import shutil
import platform
import screeninfo
import selenium
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from dataclasses import dataclass

# Selenium session module


def __cleanup_resources():
    if platform.system() == "Windows":
        folder_path = os.path.join(os.environ["LOCALAPPDATA"], "Temp")
    elif platform.system() == "Linux":
        folder_path = "/tmp"
    else:
        return

    for filename in os.listdir(folder_path):
        full_path = os.path.join(folder_path, filename)
        if os.path.isdir(full_path):
            for dirPrefix in ["tmp", "rust_mozpr"]:
                if filename.startswith(dirPrefix):
                    shutil.rmtree(full_path)
                    break


def __get_firefox_options(
    firefox_profile: str = "", headless: bool = False, private_mode: bool = False
) -> selenium.webdriver.firefox.options.Options:
    """Returns chrome options instance with given configuration set"""
    options = FirefoxOptions()
    options.profile = (
        __get_default_firefox_profile() if not firefox_profile else firefox_profile
    )

    if headless:
        monitor = screeninfo.get_monitors()[0]
        options.add_argument("--headless")
        options.add_argument(f"--window-size={monitor.width},{monitor.height}")
        options.add_argument("--start-maximized")
        options.set_preference("media.volume_scale", "0.0")

        # Opt
        options.set_preference("browser.cache.disk.enable", False)
        options.set_preference("browser.cache.memory.enable", False)
        options.set_preference("browser.cache.offline.enable", False)
        options.set_preference("network.http.use-cache", False)

    if private_mode:
        options.set_preference(
            "browser.privatebrowsing.autostart", True
        )  # Start in private mode

    return options


def __get_firefox_webdriver(
    *args, use_selwire: bool = False, **kwargs
) -> selenium.webdriver:
    """Constructor wrapper for Firefox webdriver"""

    if platform.system() == "Windows":
        # Check if firefox is in PATH
        DEFAULT_WINDWOS_FIREFOX_PATH = "C:\\Program Files\\Mozilla Firefox"
        if (
            not shutil.which("firefox")
            and os.environ["PATH"].find(DEFAULT_WINDWOS_FIREFOX_PATH) == -1
        ):
            os.environ["PATH"] += f";{DEFAULT_WINDWOS_FIREFOX_PATH}"

    if use_selwire:
        from seleniumwire import webdriver

        return webdriver.Firefox(*args, **kwargs)
    return selenium.webdriver.Firefox(*args, **kwargs)


def __linux_default_firefox_profile_path() -> str:
    profile_path = os.path.expanduser("~/.mozilla/firefox")

    if not os.path.exists(profile_path):
        raise RuntimeError(f"Unable to retrieve {profile_path} directory")

    for entry in os.listdir(profile_path):
        if entry.endswith(".default-release"):
            return os.path.join(profile_path, entry)
    return None


def __win_default_firefox_profile_path() -> str:
    profile_path = os.path.join(os.getenv("APPDATA"), "Mozilla\Firefox\Profiles")
    for entry in os.listdir(profile_path):
        if entry.endswith(".default-release"):
            return os.path.join(profile_path, entry)
    return None


def __get_default_firefox_profile() -> str:
    if platform.system() == "Windows":
        return __win_default_firefox_profile_path()
    elif platform.system() == "Linux":
        return __linux_default_firefox_profile_path()
    return ""


@dataclass(frozen=True)
class SessionData:
    """
    This session class will be passed to `ClaudeAPIClient` constructor.

    It can be auto generated by having a working login in Firefox, and geckodriver installed, calling `get_session_data()`
    with the Firefox profile path, or the default one if omitted.
    """

    cookie: str
    """
    The entire Cookie header string value
    """
    user_agent: str
    """
    Browser User agent
    """


def get_session_data(profile: str = "", quiet: bool = False) -> SessionData | None:
    """
    Retrieves Claude session data

    This function requires a profile with Claude login and geckodriver installed!

    The default Firefox profile will be used, if the profile argument was not overwrited.
    """

    __BASE_CHAT_URL = "https://claude.ai/chats"
    if not profile:
        profile = __get_default_firefox_profile()

    if not quiet:
        print(f"\nRetrieving {__BASE_CHAT_URL} session cookie from {profile}")

    __cleanup_resources()
    opts = __get_firefox_options(firefox_profile=profile, headless=True)
    driver = __get_firefox_webdriver(options=opts)
    try:
        driver.get(__BASE_CHAT_URL)

        driver.implicitly_wait(3)
        user_agent = driver.execute_script("return navigator.userAgent")
        if not user_agent:
            raise RuntimeError("Cannot retrieve UserAgent...")

        cookies = driver.get_cookies()

        cookie_string = "; ".join(
            [f"{cookie['name']}={cookie['value']}" for cookie in cookies]
        )
        return SessionData(cookie_string, user_agent)
    finally:
        driver.quit()
        __cleanup_resources()
