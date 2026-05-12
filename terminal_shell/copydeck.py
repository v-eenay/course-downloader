from downloader_core import general


def build_about_markup(app_version):
    return f"""
    <b>Course Downloader</b><br>
    Version: {app_version}<br><br>
    Local desktop build.<br>
    No remote branding or contact metadata embedded in this copy.
    """


def build_help_markup():
    supported_browsers = general.get_supported_browsers_text()
    return """
    <b>USING THE PROGRAM:</b><br>
    Enter the required information and press Download. The application keeps the transfer inside the main window so progress and logs stay visible.<br><br>
    Use CTRL+V to paste a URL.<br><br>
    You can enter either a course URL/slug, a specialization URL/slug, or a professional certificate URL. Specialization and professional certificate URLs are auto-detected, and slug inputs can still be forced with the checkbox in the main window.<br><br>
    <b>BROWSER LOGIN:</b><br>
    Automatic browser authentication works with {supported_browsers}. Make sure you are already logged in on coursera.org in the selected browser.<br><br>
    <b>VIDEO QUALITY:</b><br>
    The video resolution field accepts 1080p, 1440p, 2160p, or <i>Best available</i>. If the exact resolution is missing, the downloader uses the highest quality Coursera exposes.<br><br>
    <b>LIVE ACTIVITY:</b><br>
    The progress bar reflects the current download stage, and the log panel shows course expansion, syllabus parsing, lecture processing, and transfer output while the download is running.<br><br>
    <b>RESUME DOWNLOAD:</b><br>
    Provide the same information and folder, then click Resume to continue from the previous position.<br><br>
    <b>SPECIALIZATION DOWNLOADS:</b><br>
    When you download a specialization, the downloader expands it into child courses and stores them in a specialization/course/module/section structure.<br><br>
    <b>SUPPORT:</b> Review the logs and local configuration if something fails.
    """.format(supported_browsers=supported_browsers)