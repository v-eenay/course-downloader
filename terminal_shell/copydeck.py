from downloader_core import general


def build_about_markup(app_version):
    return f"""
    <b>Course Downloader</b><br>
    Version: {app_version}<br><br>
    Built by <b>Binay Koirala</b><br>
    <a href="mailto:koiralavinay@gmail.com" style="color:#7bcf7b;">koiralavinay@gmail.com</a><br><br>
    Downloads course materials from Coursera and Udemy.<br>
    Uses browser cookies for authentication — no credentials are stored.
    """


def build_help_markup():
    supported_browsers = general.get_supported_browsers_text()
    return """
    <b>USING THE PROGRAM:</b><br>
    Choose a provider, enter the course URL, select your browser, and press Download.
    Progress and logs stay visible in the right panel while the download runs.<br><br>
    Use Ctrl+V to paste a URL.<br><br>

    <b>COURSERA:</b><br>
    Accepts course URLs, course slugs, specialization URLs, and professional certificate URLs.
    Enable the Specialization checkbox to download a full specialization as a single operation.<br><br>

    <b>UDEMY:</b><br>
    Paste a full Udemy course URL (e.g. https://www.udemy.com/course/example/).
    You must be enrolled in the course and logged in to Udemy in the selected browser.
    Downloads videos, subtitles in all available languages, reading articles, PDFs, code files,
    and any other supplementary attachments.<br><br>

    <b>BROWSER LOGIN:</b><br>
    Works with {supported_browsers}. Log in to the course platform in your browser before starting.
    The app reads cookies directly — your credentials are never seen or stored by this program.<br><br>

    <b>VIDEO QUALITY:</b><br>
    Accepts 720p, 1080p, 1440p, 2160p, or <i>Best available</i>.
    If the exact resolution is unavailable, the next lower quality is used.<br><br>

    <b>RESUME:</b><br>
    Provide the same URL and destination folder, then click Resume to continue an interrupted download.
    Already-downloaded files are skipped automatically.<br><br>

    <b>SUPPORT:</b><br>
    Contact <a href="mailto:koiralavinay@gmail.com" style="color:#7bcf7b;">koiralavinay@gmail.com</a>
    or check the logs panel for error details.
    """.format(supported_browsers=supported_browsers)