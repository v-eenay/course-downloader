import configparser
import glob
import os
import re
import shutil
import sys
import tempfile
from collections import namedtuple

# this dictionary holds language name as key and corresponding ISO language code as value
LANG_NAME_TO_CODE_MAPPING = {'Arabic': 'ar', 'Afrikaans': 'af',
                             'Bangla': 'bn', 'Burmese': 'my',
                             'Chinese (Simplified)': 'zh-Hans', 'Chinese (Traditional)': 'zh-Hant', 'Chinese': 'zh-CN',
                             'Dutch': 'nl',
                             'English': 'en',
                             'French': 'fr', 'Finnish': 'fi',
                             'Greek': 'el',
                             'Hindi': 'hi',
                             'Italian': 'it',
                             'Japanese': 'ja',
                             'Korean': 'ko',
                             'Malay': 'ml', 'Malayalam': 'ml',
                             'Portugese': 'pt',
                             'Russian': 'ru',
                             'Spanish': 'es',
                             'Tamil': 'ta', 'Telegu': 'te', 'Thai': 'th', 'Turkish': 'tr',
                             'Urdu': 'ur',
                             'Vietnamese': 'vi',
                             '-ALL AVAILABLE': 'all', '-NONE': ''}

BROWSER_DISPLAY_NAMES = {
    "edge": "Edge",
    "chrome": "Chrome",
    "arc": "Arc",
    "zen": "Zen",
    "firefox": "Firefox",
    "brave": "Brave",
    "opera": "Opera",
    "opera_gx": "Opera GX",
    "chromium": "Chromium",
    "vivaldi": "Vivaldi",
    "librewolf": "LibreWolf",
}

if sys.platform == "darwin":
    BROWSER_DISPLAY_NAMES["safari"] = "Safari"

ALLOWED_BROWSERS = list(BROWSER_DISPLAY_NAMES.keys())

DEFAULT_VIDEO_RESOLUTION = "best"
VIDEO_RESOLUTION_OPTIONS = [
    ("Best available", "best"),
    ("2160p (4K)", "2160p"),
    ("1440p", "1440p"),
    ("1080p", "1080p"),
    ("720p", "720p"),
    ("540p", "540p"),
    ("360p", "360p"),
]
COMMON_VIDEO_RESOLUTIONS = [value for _, value in VIDEO_RESOLUTION_OPTIONS]

CourseraTarget = namedtuple('CourseraTarget', 'kind slug is_url')

_SLUG_PATTERN = re.compile(r'^[a-zA-Z0-9-]+$')
_COURSE_URL_PATTERN = re.compile(
    r'coursera\.org/(?:[^/?#]+/)*learn/([^/?#]+)',
    re.IGNORECASE
)
_SPECIALIZATION_URL_PATTERN = re.compile(
    r'coursera\.org/(?:[^/?#]+/)*specializations/([^/?#]+)',
    re.IGNORECASE
)
_PROGRAMS_SPECIALIZATION_URL_PATTERN = re.compile(
    r'coursera\.org/programs/[^/?#]+/specializations/([^/?#]+)',
    re.IGNORECASE
)
_PROFESSIONAL_CERTIFICATE_URL_PATTERN = re.compile(
    r'coursera\.org/(?:[^/?#]+/)*professional-certificates?/([^/?#]+)',
    re.IGNORECASE
)

CUSTOM_BROWSER_PATHS = {
    "arc": {
        "win32": [
            r"%LOCALAPPDATA%\Packages\TheBrowserCompany.Arc*\LocalCache\Local\Arc\User Data\Default\Network\Cookies",
            r"%LOCALAPPDATA%\Packages\TheBrowserCompany.Arc*\LocalCache\Local\Arc\User Data\Profile *\Network\Cookies",
        ],
        "darwin": [
            "~/Library/Application Support/Arc/User Data/Default/Cookies",
            "~/Library/Application Support/Arc/User Data/Profile */Cookies",
        ],
        "linux": [
            "~/snap/arc/common/arc/Default/Cookies",
            "~/.config/arc/Default/Cookies",
            "~/.config/arc/Profile */Cookies",
            "~/.var/app/org.arc.Arc/config/arc/Default/Cookies",
            "~/.var/app/org.arc.Arc/config/arc/Profile */Cookies",
        ],
    },
    "zen": {
        "win32": [r"%APPDATA%\zen", r"%LOCALAPPDATA%\zen"],
        "darwin": ["~/Library/Application Support/zen"],
        "linux": ["~/.zen"],
    },
}

WINDOWS_CHROMIUM_COOKIE_PATHS = {
    "edge": [
        r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Network\Cookies",
        r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Profile *\Network\Cookies",
    ],
    "chrome": [
        r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Network\Cookies",
        r"%LOCALAPPDATA%\Google\Chrome\User Data\Profile *\Network\Cookies",
    ],
    "arc": CUSTOM_BROWSER_PATHS["arc"]["win32"],
    "brave": [
        r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default\Network\Cookies",
        r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Profile *\Network\Cookies",
    ],
    "opera": [
        r"%APPDATA%\Opera Software\Opera Stable\Network\Cookies",
        r"%APPDATA%\Opera Software\Opera Developer\Network\Cookies",
    ],
    "opera_gx": [
        r"%APPDATA%\Opera Software\Opera GX Stable\Network\Cookies",
    ],
    "chromium": [
        r"%LOCALAPPDATA%\Chromium\User Data\Default\Network\Cookies",
        r"%LOCALAPPDATA%\Chromium\User Data\Profile *\Network\Cookies",
    ],
    "vivaldi": [
        r"%LOCALAPPDATA%\Vivaldi\User Data\Default\Network\Cookies",
        r"%LOCALAPPDATA%\Vivaldi\User Data\Profile *\Network\Cookies",
    ],
}


def get_supported_browsers_text():
    return ', '.join(BROWSER_DISPLAY_NAMES[browser] for browser in ALLOWED_BROWSERS)


def parse_coursera_target(target: str, default_kind='course'):
    if target is None:
        return None

    normalized_target = target.strip()
    if not normalized_target:
        return None

    lowered_target = normalized_target.lower()

    course_match = _COURSE_URL_PATTERN.search(lowered_target)
    if course_match:
        return CourseraTarget('course', course_match.group(1), True)

    specialization_match = _SPECIALIZATION_URL_PATTERN.search(lowered_target)
    if specialization_match:
        return CourseraTarget('specialization', specialization_match.group(1), True)

    programs_specialization_match = _PROGRAMS_SPECIALIZATION_URL_PATTERN.search(lowered_target)
    if programs_specialization_match:
        return CourseraTarget('specialization', programs_specialization_match.group(1), True)

    professional_certificate_match = _PROFESSIONAL_CERTIFICATE_URL_PATTERN.search(lowered_target)
    if professional_certificate_match:
        return CourseraTarget('specialization', professional_certificate_match.group(1), True)

    if _SLUG_PATTERN.fullmatch(normalized_target):
        if default_kind not in ('course', 'specialization'):
            default_kind = 'course'
        return CourseraTarget(default_kind, normalized_target.lower(), False)

    return None


def _get_platform_key():
    if sys.platform == "win32":
        return "win32"
    if sys.platform == "darwin":
        return "darwin"
    if sys.platform.startswith("linux") or "bsd" in sys.platform.lower():
        return "linux"
    raise RuntimeError(f"Unsupported platform: {sys.platform}")


def _iter_existing_paths(paths):
    for raw_path in paths:
        if _get_platform_key() == "win32":
            expanded_path = os.path.expandvars(raw_path)
        else:
            expanded_path = os.path.expanduser(raw_path)

        for matched_path in sorted(glob.glob(expanded_path)):
            if os.path.exists(matched_path):
                yield os.path.normpath(matched_path)


def _find_default_mozilla_profile(base_path):
    profiles_ini_path = os.path.join(base_path, "profiles.ini")
    if not os.path.exists(profiles_ini_path):
        return None

    config = configparser.ConfigParser()
    config.read(profiles_ini_path, encoding="utf8")

    profile_path = None
    for section in config.sections():
        if section.startswith("Install"):
            profile_path = config[section].get("Default")
            if profile_path:
                break
        elif config[section].get("Default") == "1" and not profile_path:
            profile_path = config[section].get("Path")

    if not profile_path:
        return None

    for section in config.sections():
        if config[section].get("Path") == profile_path:
            if config[section].get("IsRelative") == "0":
                return profile_path
            return os.path.join(os.path.dirname(profiles_ini_path), profile_path)

    return None


def _find_firefox_cookie_file(base_paths):
    for base_path in _iter_existing_paths(base_paths):
        candidate_patterns = []
        default_profile = _find_default_mozilla_profile(base_path)
        if default_profile:
            candidate_patterns.append(os.path.join(default_profile, "cookies.sqlite"))

        candidate_patterns.extend([
            os.path.join(base_path, "Profiles", "*", "cookies.sqlite"),
            os.path.join(base_path, "*", "cookies.sqlite"),
        ])

        for pattern in candidate_patterns:
            matches = sorted(glob.glob(pattern))
            if matches:
                return os.path.normpath(matches[0])

    raise FileNotFoundError("Could not find Firefox-style cookies.sqlite database.")


def _find_chromium_key_file(cookie_file):
    cookie_dir = os.path.dirname(cookie_file)
    for relative_parts in (("..", "..", "Local State"), ("..", "Local State"), ("Local State",)):
        candidate = os.path.normpath(os.path.join(cookie_dir, *relative_parts))
        if os.path.exists(candidate):
            return candidate

    raise FileNotFoundError(f"Could not find Local State for {cookie_file}")


def _build_browser_cookie3_direct_loaders(browser_cookie3_module):
    direct_loaders = {
        "edge": browser_cookie3_module.edge,
        "chrome": browser_cookie3_module.chrome,
        "firefox": browser_cookie3_module.firefox,
        "brave": browser_cookie3_module.brave,
        "opera": browser_cookie3_module.opera,
        "opera_gx": browser_cookie3_module.opera_gx,
        "chromium": browser_cookie3_module.chromium,
        "vivaldi": browser_cookie3_module.vivaldi,
        "librewolf": browser_cookie3_module.librewolf,
    }

    if sys.platform == "darwin" and hasattr(browser_cookie3_module, "safari"):
        direct_loaders["safari"] = browser_cookie3_module.safari

    return direct_loaders


def _load_arc_cookies_with_browser_cookie3(browser_cookie3_module, domain: str, cookie_file: str, key_file=None):
    return browser_cookie3_module.ChromiumBased(
        browser='Arc',
        cookie_file=cookie_file,
        domain_name=domain,
        key_file=key_file,
        os_crypt_name='arc',
        osx_key_service='Arc Safe Storage',
        osx_key_user='Arc'
    ).load()


def _copy_cookie_store_to_temp(cookie_file):
    _, extension = os.path.splitext(cookie_file)
    file_descriptor, temp_cookie_file = tempfile.mkstemp(
        prefix='coursera_cookie_',
        suffix=extension or '.sqlite'
    )
    os.close(file_descriptor)
    shutil.copy2(cookie_file, temp_cookie_file)
    return temp_cookie_file


def _find_windows_chromium_cookie_file(browser: str):
    cookie_patterns = WINDOWS_CHROMIUM_COOKIE_PATHS.get(browser)
    if not cookie_patterns:
        raise ValueError(f'Windows Chromium cookie lookup is not implemented for {browser}')

    cookie_file = next(_iter_existing_paths(cookie_patterns), None)
    if not cookie_file:
        raise FileNotFoundError(f'Could not find {browser} cookie database.')

    return cookie_file


def _load_browser_cookies_from_rookiepy(domain: str, browser: str):
    import rookiepy

    browser_loaders = {
        "edge": rookiepy.edge,
        "chrome": rookiepy.chrome,
        "arc": rookiepy.arc,
        "zen": rookiepy.zen,
        "firefox": rookiepy.firefox,
        "brave": rookiepy.brave,
        "opera": rookiepy.opera,
        "opera_gx": rookiepy.opera_gx,
        "chromium": rookiepy.chromium,
        "vivaldi": rookiepy.vivaldi,
        "librewolf": rookiepy.librewolf,
    }

    if sys.platform == "darwin" and hasattr(rookiepy, "safari"):
        browser_loaders["safari"] = rookiepy.safari

    return browser_loaders[browser]([domain])


def _load_browser_cookies_from_browser_cookie3(domain: str, browser: str):
    import browser_cookie3

    direct_loaders = _build_browser_cookie3_direct_loaders(browser_cookie3)

    if browser in direct_loaders:
        return direct_loaders[browser](domain_name=domain)

    platform_key = _get_platform_key()

    if browser == "zen":
        cookie_file = _find_firefox_cookie_file(CUSTOM_BROWSER_PATHS["zen"][platform_key])
        return browser_cookie3.firefox(cookie_file=cookie_file, domain_name=domain)

    if browser == "arc":
        cookie_file = next(_iter_existing_paths(CUSTOM_BROWSER_PATHS["arc"][platform_key]), None)
        if not cookie_file:
            raise FileNotFoundError("Could not find Arc cookie database.")

        key_file = _find_chromium_key_file(cookie_file) if platform_key == "win32" else None
        return _load_arc_cookies_with_browser_cookie3(browser_cookie3, domain, cookie_file, key_file)

    raise ValueError(f"Browser backend not implemented for {browser}")


def _load_browser_cookies_from_windows_copy(domain: str, browser: str):
    if sys.platform != 'win32':
        raise RuntimeError('Windows cookie copy fallback is only available on Windows.')

    import browser_cookie3

    direct_loaders = _build_browser_cookie3_direct_loaders(browser_cookie3)
    temp_cookie_file = None

    try:
        if browser == 'zen':
            cookie_file = _find_firefox_cookie_file(CUSTOM_BROWSER_PATHS['zen']['win32'])
            temp_cookie_file = _copy_cookie_store_to_temp(cookie_file)
            return browser_cookie3.firefox(cookie_file=temp_cookie_file, domain_name=domain)

        if browser == 'arc':
            cookie_file = _find_windows_chromium_cookie_file('arc')
            key_file = _find_chromium_key_file(cookie_file)
            temp_cookie_file = _copy_cookie_store_to_temp(cookie_file)
            return _load_arc_cookies_with_browser_cookie3(browser_cookie3, domain, temp_cookie_file, key_file)

        if browser in WINDOWS_CHROMIUM_COOKIE_PATHS and browser in direct_loaders:
            cookie_file = _find_windows_chromium_cookie_file(browser)
            key_file = _find_chromium_key_file(cookie_file)
            temp_cookie_file = _copy_cookie_store_to_temp(cookie_file)
            return direct_loaders[browser](
                cookie_file=temp_cookie_file,
                domain_name=domain,
                key_file=key_file,
            )

        raise ValueError(f'Windows cookie copy fallback is not implemented for {browser}')
    finally:
        if temp_cookie_file and os.path.exists(temp_cookie_file):
            os.remove(temp_cookie_file)


def _load_browser_cookies_from_locked_cookie(domain: str, browser: str):
    if sys.platform != 'win32':
        raise ValueError(f'Locked-cookie fallback is not implemented for {browser}')

    import browser_cookie3
    from locked_cookie import fetch_locked_chromium_cookies

    direct_loaders = _build_browser_cookie3_direct_loaders(browser_cookie3)

    if browser == 'arc':
        loader = lambda cookie_file=None, domain_name='', key_file=None: _load_arc_cookies_with_browser_cookie3(
            browser_cookie3,
            domain_name,
            cookie_file,
            key_file,
        )
    else:
        loader = direct_loaders.get(browser)

    if loader is None or browser not in WINDOWS_CHROMIUM_COOKIE_PATHS:
        raise ValueError(f'Locked-cookie fallback is not implemented for {browser}')

    cookie_file = _find_windows_chromium_cookie_file(browser)
    key_file = _find_chromium_key_file(cookie_file)

    return fetch_locked_chromium_cookies(domain, cookie_file, loader, key_file=key_file)


# yt-dlp browser name mapping  (yt-dlp knows edge/chrome/brave/vivaldi/opera/chromium)
_YTDLP_BROWSER_MAP = {
    "edge":     "edge",
    "chrome":   "chrome",
    "brave":    "brave",
    "vivaldi":  "vivaldi",
    "opera":    "opera",
    "opera_gx": "opera",
    "chromium": "chromium",
}


def _load_browser_cookies_from_ytdlp(domain: str, browser: str):
    """Use yt-dlp's cookie extraction which handles Edge/Chrome 127+ APPB encryption.

    yt-dlp decrypts app-bound cookies without requiring admin rights or closing
    the browser.  It's tried *first* so that the APPB-capable path is preferred
    over the older browser_cookie3 path that only supports DPAPI keys.
    """
    ytdlp_name = _YTDLP_BROWSER_MAP.get(browser)
    if not ytdlp_name:
        raise ValueError(f"yt-dlp cookie extraction not available for {browser}")

    try:
        from yt_dlp.cookies import extract_cookies_from_browser, YDLLogger
    except ImportError as exc:
        raise ImportError(f"yt-dlp is not installed: {exc}") from exc

    class _SilentLogger(YDLLogger):
        def warning(self, message): pass
        def error(self, message): pass

    jar = extract_cookies_from_browser(ytdlp_name, logger=_SilentLogger())

    # Filter to the requested domain (yt-dlp returns ALL cookies for the browser)
    matching = [
        c for c in jar
        if domain.lstrip(".") in c.domain or c.domain.lstrip(".") in domain.lstrip(".")
    ]
    # If domain is a broad term like "udemy" just return everything from any udemy host
    if not matching and len(domain) <= 6:
        matching = list(jar)
    return matching if matching else list(jar)


def load_browser_cookies(domain: str, browser: str):
    if browser not in ALLOWED_BROWSERS:
        raise ValueError(
            "Browser not supported. Please login on one of these browsers: "
            f"{get_supported_browsers_text()}"
        )

    backend_errors = []
    backends = [
        ("yt-dlp", _load_browser_cookies_from_ytdlp),
        ("rookiepy", _load_browser_cookies_from_rookiepy),
        ("browser_cookie3", _load_browser_cookies_from_browser_cookie3),
    ]
    if sys.platform == 'win32':
        backends.append(("windows_cookie_copy", _load_browser_cookies_from_windows_copy))
        if browser in WINDOWS_CHROMIUM_COOKIE_PATHS:
            # Skip locked_cookie (which uses RmShutdown to kill the browser process)
            # when already running elevated — admin can read the cookie file directly
            # via windows_cookie_copy without killing the browser.
            _elevated = False
            try:
                import ctypes as _ctypes
                _elevated = bool(_ctypes.windll.shell32.IsUserAnAdmin())
            except Exception:
                pass
            if not _elevated:
                backends.append(("locked_cookie", _load_browser_cookies_from_locked_cookie))

    for backend_name, loader in backends:
        try:
            return loader(domain, browser)
        except (ImportError, ModuleNotFoundError) as error:
            if backend_name in ('rookiepy', 'yt-dlp'):
                continue  # optional backends – skip silently if not installed
            backend_errors.append(f"{backend_name}: {error}")
        except Exception as error:
            backend_errors.append(f"{backend_name}: {error}")

    if not backend_errors:
        raise RuntimeError('No supported cookie backend is available.')

    raise RuntimeError('; '.join(backend_errors))


def _extract_cauth_from_cookies(cookies):
    cauth = ""

    for cookie in cookies:
        cookie_name = getattr(cookie, 'name', None)
        cookie_value = getattr(cookie, 'value', None)

        if cookie_name is None and isinstance(cookie, dict):
            cookie_name = cookie.get('name')
            cookie_value = cookie.get('value')

        if cookie_name == "CAUTH":
            if cookie_value:
                return cookie_value
            cauth = cookie_value

    return cauth


def _loadcauth_from_single_browser(domain: str, browser: str):
    try:
        cookies = load_browser_cookies(domain, browser)
    except Exception as error:
        detail = str(error).strip() or error.__class__.__name__
        return "", detail

    cauth = _extract_cauth_from_cookies(cookies)
    if cauth:
        return cauth, None

    return cauth, 'No CAUTH cookie was found in the selected browser session.'

# extract class name from course home page url
def urltoclassname(homepageurl):
    '''this function assumes that the url is of this possible format:
    1. https://www.coursera.org/learn/model-thinking
    2. https://www.coursera.org/learn/model-thinking/home/week/1
    3. https://www.coursera.org/learn/model-thinking?specialization=deep-learning

    if the url isn't in this format, program won't work'''

    target = parse_coursera_target(homepageurl, default_kind='course')
    if target and target.kind == 'course':
        return target.slug
    return ""


def loadcauth_result(domain: str, browser: str):
    """Return the CAUTH value, an optional error string, and the browser that provided it."""
    cauth, error = _loadcauth_from_single_browser(domain, browser)
    if cauth:
        return cauth, None, browser

    for fallback_browser in ALLOWED_BROWSERS:
        if fallback_browser == browser:
            continue

        fallback_cauth, _ = _loadcauth_from_single_browser(domain, fallback_browser)
        if fallback_cauth:
            return fallback_cauth, None, fallback_browser

    return cauth, error, browser


def loadcauth(domain: str, browser: str):
    """Return the CAUTH code for the selected browser, or an empty string on failure."""
    return loadcauth_result(domain, browser)[0]


def move_to_first(dictionary, key):
    if key not in dictionary:
        return dictionary  # Key not found, no changes needed

    value = dictionary[key]
    # Create a new dictionary with the desired key-value pair as the first item
    new_dict = {key: value}

    for k, v in dictionary.items():
        if k != key:
            # Insert the remaining key-value pairs into the new dictionary
            new_dict[k] = v

    return new_dict

# testing urltoclassname function
# url = "https://www.coursera.org/learn/model-thinking"
# url = "https://www.coursera.org/learn/model-thinking/home/week/1"
# url = "https://www.coursera.org/learn/neural-networks-deep-learning?specialization=deep-learning"
# url = "https://www.coursera.org/learn/java-programming-recommender/home/week/1https://www.coursera.org/learn/java-programming-recommender/home/week/1"
# url = "model-thinking-hell"
# url = "model-thinking?"
# cn = urltoclassname(url)
# print(cn)
if __name__ == "__main__":
    ca = loadcauth('coursera.org', browser='zen')
    print(ca)