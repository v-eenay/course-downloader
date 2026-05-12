from downloader_core.coursera_dl import *#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Authors and copyright:
#     © 2012-2013, John Lehmann (first last at geemail dotcom or @jplehmann)
#     © 2012-2020, Rogério Theodoro de Brito
#     © 2013, Jonas De Taeye (first dt at fastmail fm)
#
# Contributions are welcome, but please add new unit tests to test your changes
# and/or features.  Also, please try to make changes platform independent and
# backward compatible.
#
# Legalese:
#
#  This program is free software: you can redistribute it and/or modify it
#  under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or (at your
#  option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""
Module for downloading lecture resources such as videos for Coursera classes.

Given a class name, username and password, it scrapes the course listing
page to get the section (week) and lecture names, and then downloads the
related materials into appropriately named files and directories.

Examples:
    python coursera_dl.py --cauth <token> saas
    python coursera_dl.py --cauth-auto chrome saas --skip-download
"""


import json
import logging
import os
import re
import time
import shutil

from packaging.version import parse as V


# Test versions of some critical modules.
# We may, perhaps, want to move these elsewhere.
import bs4
import requests

from cookies import (
    AuthenticationFailed, ClassNotFound,
    get_cookies_for_class, make_cookie_values, TLSAdapter, login)
from define import (CLASS_URL, ABOUT_URL, PATH_CACHE)
from downloaders import get_downloader
from workflow import CourseraDownloader
from parallel import ConsecutiveDownloader, ParallelDownloader
from utils import (clean_filename, get_anchor_format, mkdir_p, fix_url,
                   print_ssl_error_message,
                   BeautifulSoup, is_debug_run,
                   spit_json, slurp_json)

from api import resolve_download_targets
from general import loadcauth
from network import get_page, get_page_and_url
from commandline import parse_args
from extractors import CourseraExtractor


# URL containing information about outdated modules
_SEE_URL = " Review the local dependency requirements."

assert V(requests.__version__) >= V('2.4'), "Upgrade requests!" + _SEE_URL
assert V(bs4.__version__) >= V('4.1'), "Upgrade bs4!" + _SEE_URL


def get_session():
    """
    Create a session with TLS v1.2 certificate.
    """

    session = requests.Session()
    session.mount('https://', TLSAdapter())

    return session


def create_session(args):
    session = get_session()
    if args.cookies_cauth:
        session.cookies.set('CAUTH', args.cookies_cauth)
    elif args.browser:
        cauth_cookie = loadcauth('coursera.org', args.browser)
        if not cauth_cookie:
            raise RuntimeError(
                f'Could not load CAUTH from {args.browser}. Make sure you are '
                'logged in on coursera.org in the selected browser.'
            )
        logging.debug('Loaded CAUTH cookie from %s.', args.browser)
        session.cookies.set('CAUTH', cauth_cookie)
    else:
        login(session, args.username, args.password)
    return session


def list_courses(args):
    """
    List enrolled courses.

    @param args: Command-line arguments.
    @type args: namedtuple
    """
    session = create_session(args)
    extractor = CourseraExtractor(session)
    courses = extractor.list_courses()
    logging.info('Found %d courses', len(courses))
    for course in courses:
        logging.info(course)


def download_on_demand_class(session, args, class_name, download_path=None):
    """
    Download all requested resources from the on-demand class given
    in class_name.

    @return: Tuple of (bool, bool), where the first bool indicates whether
        errors occurred while parsing syllabus, the second bool indicates
        whether the course appears to be completed.
    @rtype: (bool, bool)
    """

    error_occurred = False
    extractor = CourseraExtractor(session)

    cached_syllabus_filename = '%s-syllabus-parsed.json' % class_name
    if args.cache_syllabus and os.path.isfile(cached_syllabus_filename):
        modules = slurp_json(cached_syllabus_filename)
    else:
        error_occurred, modules = extractor.get_modules(
            class_name,
            args.reverse,
            args.unrestricted_filenames,
            args.subtitle_language,
            args.video_resolution,
            args.download_quizzes,
            args.mathjax_cdn_url,
            args.download_notebooks
        )

    if is_debug_run or args.cache_syllabus():
        spit_json(modules, cached_syllabus_filename)

    if args.only_syllabus:
        return error_occurred, False

    downloader = get_downloader(session, class_name, args)
    downloader_wrapper = ParallelDownloader(downloader, args.jobs) \
        if args.jobs > 1 else ConsecutiveDownloader(downloader)

    # obtain the resources

    ignored_formats = []
    if args.ignore_formats:
        ignored_formats = args.ignore_formats.split(",")

    course_downloader = CourseraDownloader(
        downloader_wrapper,
        commandline_args=args,
        class_name=class_name,
        path=download_path if download_path is not None else args.path,
        ignored_formats=ignored_formats,
        disable_url_skipping=args.disable_url_skipping
    )

    completed = course_downloader.download_modules(modules)

    # Print skipped URLs if any
    if course_downloader.skipped_urls:
        print_skipped_urls(course_downloader.skipped_urls)

    # Print failed URLs if any
    # FIXME: should we set non-zero exit code if we have failed URLs?
    if course_downloader.failed_urls:
        print_failed_urls(course_downloader.failed_urls)

    return error_occurred, completed


def print_skipped_urls(skipped_urls):
    logging.info('The following URLs (%d) have been skipped and not '
                 'downloaded:', len(skipped_urls))
    logging.info('(if you want to download these URLs anyway, please '
                 'add "--disable-url-skipping" option)')
    logging.info('-' * 80)
    for url in skipped_urls:
        logging.info(url)
    logging.info('-' * 80)


def print_failed_urls(failed_urls):
    logging.info('The following URLs (%d) could not be downloaded:',
                 len(failed_urls))
    logging.info('-' * 80)
    for url in failed_urls:
        logging.info(url)
    logging.info('-' * 80)


def download_class(session, args, class_name, download_path=None):
    """
    Try to download on-demand class.

    @return: Tuple of (bool, bool), where the first bool indicates whether
        errors occurred while parsing syllabus, the second bool indicates
        whether the course appears to be completed.
    @rtype: (bool, bool)
    """
    logging.debug('Downloading new style (on demand) class %s', class_name)
    return download_on_demand_class(session, args, class_name, download_path)


def main_f(cmd):
    """
    Main entry point for execution as a program (instead of as a module).
    """
    # cmd is the usual command line instructions
    # ==================
    args = parse_args(cmd)
    # ===================
    logging.info('>> COURSE DOWNLOADER\n')
    completed_classes = []
    classes_with_errors = []

    mkdir_p(PATH_CACHE, 0o700)
    if args.clear_cache:
        shutil.rmtree(PATH_CACHE)
    if args.list_courses:
        logging.info('Listing enrolled courses')
        list_courses(args)
        return

    session = create_session(args)

    download_targets = resolve_download_targets(
        session,
        args.class_names,
        base_path=args.path,
        specialization_hint=args.specialization
    )

    for class_index, target in enumerate(download_targets):
        try:
            logging.info('Downloading class: %s (%d / %d)',
                         target.class_name, class_index + 1, len(download_targets))
            error_occurred, completed = download_class(
                session, args, target.class_name, download_path=target.path)
            if completed:
                completed_classes.append(target.class_name)
            if error_occurred:
                classes_with_errors.append(target.class_name)
        except requests.exceptions.HTTPError as e:
            # logging.error('HTTPError %s', e)
            # if is_debug_run():
            #     logging.exception('HTTPError %s', e)
            
            raise # raise error
            
        except requests.exceptions.SSLError as e:
            # logging.error('SSLError %s', e)
            # print_ssl_error_message(e)
            if is_debug_run():
                raise
            
            raise

        except ClassNotFound as e:
            logging.error('Could not find class: %s', e)
            raise
        except AuthenticationFailed as e:
            logging.error('Could not authenticate: %s', e)
            raise

        if class_index + 1 != len(download_targets):
            logging.info('Sleeping for %d seconds before downloading next course. '
                         'You can change this with --download-delay option.',
                         args.download_delay)
            time.sleep(args.download_delay)

    if completed_classes:
        logging.info('-' * 80)
        logging.info(
            "Classes which appear completed: " + " ".join(completed_classes))

    if classes_with_errors:
        logging.info('-' * 80)
        logging.info('The following classes had errors during the syllabus'
                     ' parsing stage. You may want to review error messages and'
                     ' courses (sometimes enrolling to the course or switching'
                     ' session helps):')
        for class_name in classes_with_errors:
            logging.info('%s (https://www.coursera.org/learn/%s)',
                         class_name, class_name)
