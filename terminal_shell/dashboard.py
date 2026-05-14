import sys
from os import path

from PyQt5.QtCore import QThread, QTimer, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from downloader_core import general
from downloader_core.providers import get_provider, provider_choices
from app_metadata import APP_VERSION
from settings_store import SettingsStore
from terminal_shell.bridge import TransferCoordinator
from terminal_shell.copydeck import build_about_markup, build_help_markup
from terminal_shell.paint import PHOSPHOR_STYLESHEET, svg_to_pixmap


class ConsoleDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Course Downloader")
        self.setMinimumSize(780, 560)
        self.resize(980, 680)

        project_root = path.abspath(path.join(path.dirname(__file__), '..'))
        self.logo_path = path.join(project_root, 'icon', 'course-downloader-logo.svg')
        logo = svg_to_pixmap(self.logo_path, 256)
        if not logo.isNull():
            self.setWindowIcon(QIcon(logo))

        self.language_choices = general.LANG_NAME_TO_CODE_MAPPING
        self.browser_choices = general.ALLOWED_BROWSERS
        self.provider_options = provider_choices()
        self.active_thread = None
        self.transfer_bridge = None
        self.running_provider_name = "Course Provider"
        self._queued_lines = []
        self.log_timer = QTimer(self)
        self.log_timer.setInterval(90)
        self.log_timer.setSingleShot(True)
        self.log_timer.timeout.connect(self._drain_log_buffer)

        self.preference_store = SettingsStore('data.bin')
        self.saved_options = self.preference_store.get_full_db()['argdict']

        self._compose_ui()

    def _compose_ui(self):
        self.setStyleSheet(PHOSPHOR_STYLESHEET)

        menu_bar = self.menuBar()
        help_menu = menu_bar.addMenu("Menu")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._open_about)
        help_action = QAction("Help", self)
        help_action.triggered.connect(self._open_help)
        help_menu.addAction(about_action)
        help_menu.addAction(help_action)

        root_widget = QWidget()
        self.setCentralWidget(root_widget)
        root_layout = QVBoxLayout()
        root_widget.setLayout(root_layout)
        root_layout.setSpacing(8)
        root_layout.setContentsMargins(10, 10, 10, 10)

        title_bar = QFrame()
        title_bar.setObjectName("TopBar")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(12, 10, 12, 10)
        title_layout.setSpacing(12)

        badge_art = QLabel()
        badge_art.setFixedSize(48, 48)
        badge_icon = svg_to_pixmap(self.logo_path, 96)
        if not badge_icon.isNull():
            badge_art.setPixmap(badge_icon.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        title_layout.addWidget(badge_art, 0, Qt.AlignVCenter)

        heading_layout = QVBoxLayout()
        heading_layout.setSpacing(2)

        heading = QLabel("Course Downloader")
        heading.setObjectName("HeroTitle")
        heading_layout.addWidget(heading)

        subheading = QLabel("Courses and specializations")
        subheading.setObjectName("HeroSubtitle")
        subheading.setWordWrap(True)
        heading_layout.addWidget(subheading)
        title_layout.addLayout(heading_layout, 1)

        self.state_badge = QLabel("Idle")
        self.state_badge.setObjectName("StateBadge")
        self.state_badge.setMinimumWidth(100)
        self.state_badge.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(self.state_badge, 0, Qt.AlignTop | Qt.AlignRight)
        self._refresh_state_badge("idle", "Idle")
        root_layout.addWidget(title_bar)

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(6)
        root_layout.addWidget(self.main_splitter, 1)

        options_scroll = QScrollArea()
        options_scroll.setWidgetResizable(True)
        options_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        options_panel = QFrame()
        options_panel.setObjectName("Panel")
        options_layout = QVBoxLayout(options_panel)
        options_layout.setContentsMargins(14, 14, 14, 14)
        options_layout.setSpacing(12)

        options_heading = QLabel("Setup")
        options_heading.setObjectName("SectionTitle")
        options_layout.addWidget(options_heading)

        provider_box = QGroupBox("Provider")
        provider_layout = QVBoxLayout(provider_box)
        provider_layout.setSpacing(8)

        self.provider_select = QComboBox()
        for provider_key, provider_name in self.provider_options:
            self.provider_select.addItem(provider_name, provider_key)
        default_provider = self.preference_store.read('provider') or 'coursera'
        default_provider_index = self.provider_select.findData(default_provider)
        if default_provider_index != -1:
            self.provider_select.setCurrentIndex(default_provider_index)
        self.provider_select.currentIndexChanged.connect(self._apply_provider_ui)
        provider_layout.addWidget(self.provider_select)
        options_layout.addWidget(provider_box)

        browser_box = QGroupBox("Browser")
        browser_layout = QVBoxLayout(browser_box)
        browser_layout.setSpacing(8)

        self.browser_select = QComboBox()
        for browser in self.browser_choices:
            self.browser_select.addItem(general.BROWSER_DISPLAY_NAMES[browser], browser)
        default_browser = self.preference_store.read('browser')
        default_index = self.browser_select.findData(default_browser)
        if default_index != -1:
            self.browser_select.setCurrentIndex(default_index)
        browser_layout.addWidget(self.browser_select)
        options_layout.addWidget(browser_box)

        target_box = QGroupBox("Download")
        target_layout = QGridLayout(target_box)
        target_layout.setHorizontalSpacing(10)
        target_layout.setVerticalSpacing(8)

        self.target_label = self._make_field_label("URL or slug")
        target_layout.addWidget(self.target_label, 0, 0, 1, 2)
        self.target_input = QLineEdit(self.saved_options['classname'])
        self.target_input.setPlaceholderText("Course, specialization, or certificate")
        target_layout.addWidget(self.target_input, 1, 0, 1, 2)

        self.target_hint = QLabel()
        self.target_hint.setObjectName("SectionHint")
        self.target_hint.setWordWrap(True)
        target_layout.addWidget(self.target_hint, 2, 0, 1, 2)

        target_layout.addWidget(self._make_field_label("Folder"), 3, 0, 1, 2)
        folder_line = QHBoxLayout()
        folder_line.setSpacing(8)

        self.folder_input = QLineEdit(self.saved_options['path'])
        self.folder_input.setReadOnly(True)
        self.folder_input.setPlaceholderText("Select folder")
        folder_line.addWidget(self.folder_input, 1)

        self.folder_button = QPushButton("Browse")
        self.folder_button.clicked.connect(self._pick_output_folder)
        folder_line.addWidget(self.folder_button)
        target_layout.addLayout(folder_line, 4, 0, 1, 2)

        self.mode_label = self._make_field_label("Mode")
        target_layout.addWidget(self.mode_label, 5, 0)
        self.specialization_toggle = QCheckBox("Specialization")
        target_layout.addWidget(self.specialization_toggle, 5, 1)

        target_layout.addWidget(self._make_field_label("Video"), 6, 0)
        self.quality_select = QComboBox()
        self.quality_select.setEditable(True)
        for label, value in general.VIDEO_RESOLUTION_OPTIONS:
            self.quality_select.addItem(label, value)
        saved_quality = self.preference_store.read('argdict')['video_resolution'] or general.DEFAULT_VIDEO_RESOLUTION
        saved_quality_index = self.quality_select.findData(saved_quality)
        if saved_quality_index != -1:
            self.quality_select.setCurrentIndex(saved_quality_index)
        else:
            self.quality_select.setEditText(saved_quality)
        target_layout.addWidget(self.quality_select, 6, 1)

        target_layout.addWidget(self._make_field_label("Subtitles"), 7, 0)
        self.subtitle_select = QComboBox()
        self.subtitle_select.addItems(sorted(self.language_choices.keys()))
        subtitle_key = next(
            (key for key, value in self.language_choices.items() if value == self.preference_store.read('argdict')['sl']),
            None,
        )
        self.subtitle_select.setCurrentText(subtitle_key if subtitle_key else 'English')
        target_layout.addWidget(self.subtitle_select, 7, 1)
        options_layout.addWidget(target_box)

        action_box = QGroupBox("Actions")
        action_layout = QHBoxLayout(action_box)
        action_layout.setSpacing(10)

        self.resume_button = QPushButton("Resume")
        self.resume_button.clicked.connect(self._handle_resume_request)
        action_layout.addWidget(self.resume_button)

        self.download_button = QPushButton("Download")
        self.download_button.setObjectName("PrimaryButton")
        self.download_button.clicked.connect(self._handle_download_request)
        action_layout.addWidget(self.download_button)
        options_layout.addWidget(action_box)

        udemy_org_box = QGroupBox("Udemy Business Org (optional)")
        udemy_org_layout = QVBoxLayout(udemy_org_box)
        udemy_org_layout.setSpacing(6)
        self.udemy_org_input = QLineEdit(self.preference_store.read('udemy_org') or '')
        self.udemy_org_input.setPlaceholderText("e.g. ingnepal  (leave blank for personal accounts)")
        udemy_org_layout.addWidget(self.udemy_org_input)
        udemy_org_hint = QLabel(
            "If your Udemy account is on a business portal (yourorg.udemy.com), "
            "enter the org name here. Pasting the full business URL also works."
        )
        udemy_org_hint.setObjectName("SectionHint")
        udemy_org_hint.setWordWrap(True)
        udemy_org_layout.addWidget(udemy_org_hint)
        options_layout.addWidget(udemy_org_box)
        self.udemy_org_box = udemy_org_box

        self.browser_note = QLabel()
        self.browser_note.setObjectName("SectionHint")
        self.browser_note.setWordWrap(True)
        options_layout.addWidget(self.browser_note)
        options_layout.addStretch(1)

        options_scroll.setWidget(options_panel)
        self.main_splitter.addWidget(options_scroll)

        activity_panel = QFrame()
        activity_panel.setObjectName("Panel")
        activity_layout = QVBoxLayout(activity_panel)
        activity_layout.setContentsMargins(14, 14, 14, 14)
        activity_layout.setSpacing(10)

        activity_header = QHBoxLayout()
        activity_title = QLabel("Logs")
        activity_title.setObjectName("SectionTitle")
        activity_header.addWidget(activity_title)
        activity_header.addStretch(1)

        self.clear_button = QPushButton("Clear Log")
        self.clear_button.setObjectName("GhostButton")
        self.clear_button.clicked.connect(self._wipe_log)
        activity_header.addWidget(self.clear_button)
        activity_layout.addLayout(activity_header)

        self.status_label = QLabel("Ready.")
        self.status_label.setObjectName("StatusText")
        self.status_label.setWordWrap(True)
        activity_layout.addWidget(self.status_label)

        self.progress_meter = QProgressBar()
        self.progress_meter.setRange(0, 100)
        self.progress_meter.setValue(0)
        self.progress_meter.setFormat("Idle")
        activity_layout.addWidget(self.progress_meter)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Logs")
        self.log_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        activity_layout.addWidget(self.log_view, 1)

        self.main_splitter.addWidget(activity_panel)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)

        footer_strip = QFrame()
        footer_strip.setObjectName("StatusStrip")
        footer_layout = QHBoxLayout(footer_strip)
        footer_layout.setContentsMargins(8, 4, 8, 4)
        footer_layout.setSpacing(8)

        self.footer_label = QLabel("Ready")
        self.footer_label.setObjectName("StatusBarText")
        footer_layout.addWidget(self.footer_label, 1)
        root_layout.addWidget(footer_strip)

        self.mutable_widgets = [
            self.provider_select,
            self.browser_select,
            self.target_input,
            self.specialization_toggle,
            self.folder_input,
            self.folder_button,
            self.quality_select,
            self.subtitle_select,
            self.udemy_org_input,
            self.resume_button,
            self.download_button,
        ]

        self._apply_provider_ui()
        self._refresh_splitter()

    def _make_field_label(self, text):
        label = QLabel(text)
        label.setObjectName("InlineLabel")
        return label

    def _refresh_state_badge(self, state, text):
        self.state_badge.setText(text)
        self.state_badge.setProperty("state", state)
        self.state_badge.style().unpolish(self.state_badge)
        self.state_badge.style().polish(self.state_badge)

    def _toggle_inputs(self, active):
        for widget in self.mutable_widgets:
            if widget is self.folder_input:
                continue
            widget.setEnabled(not active)

        self.clear_button.setEnabled(True)
        if active:
            self._refresh_state_badge("active", "Running")
        else:
            self.download_button.setEnabled(True)
            self.resume_button.setEnabled(True)

    def _queue_log_line(self, line):
        line = line.strip()
        if not line:
            return

        self._queued_lines.append(line)
        if len(self._queued_lines) >= 12:
            self._drain_log_buffer()
            return
        if not self.log_timer.isActive():
            self.log_timer.start()

    def _drain_log_buffer(self):
        self.log_timer.stop()
        if not self._queued_lines:
            return

        self.log_view.appendPlainText("\n".join(self._queued_lines))
        self._queued_lines.clear()
        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _wipe_log(self):
        self._queued_lines.clear()
        self.log_timer.stop()
        self.log_view.clear()

    def _mask_command(self, arguments):
        masked = []
        hide_next = False
        for token in arguments:
            if hide_next:
                masked.append('<hidden>')
                hide_next = False
                continue

            masked.append(token)
            if token in ('-ca', '--cauth'):
                hide_next = True
        return masked

    def _set_status(self, text):
        self.status_label.setText(text)
        self.footer_label.setText(text)

    def _current_provider(self):
        provider_key = self.provider_select.currentData() or self.preference_store.read('provider') or 'coursera'
        return get_provider(provider_key)

    def _apply_provider_ui(self, *_args):
        provider = self._current_provider()
        ui_spec = provider.ui_spec
        self.target_label.setText(ui_spec.target_label)
        self.target_input.setPlaceholderText(ui_spec.target_placeholder)
        self.target_hint.setText(ui_spec.target_help)
        self.browser_note.setText(ui_spec.browser_help.format(browsers=general.get_supported_browsers_text()))
        self.mode_label.setVisible(ui_spec.show_mode_toggle)
        self.specialization_toggle.setVisible(ui_spec.show_mode_toggle)
        self.specialization_toggle.setEnabled(ui_spec.show_mode_toggle)
        self.specialization_toggle.setText(ui_spec.mode_toggle_text)
        if not ui_spec.show_mode_toggle:
            self.specialization_toggle.setChecked(False)

        provider = self._current_provider()
        self.udemy_org_box.setVisible(provider.key == 'udemy')

    def _show_message_box(self, title, text, icon):
        dialog = QMessageBox(self)
        dialog.setIcon(icon)
        dialog.setWindowTitle(title)
        dialog.setTextFormat(Qt.PlainText)
        dialog.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        dialog.setText(text)
        dialog.setStandardButtons(QMessageBox.Ok)
        dialog.exec_()

    def _refresh_splitter(self):
        if self.width() < 920:
            orientation = Qt.Vertical
            sizes = [320, 420]
        else:
            orientation = Qt.Horizontal
            sizes = [340, 620]

        if self.main_splitter.orientation() != orientation:
            self.main_splitter.setOrientation(orientation)
        self.main_splitter.setSizes(sizes)

    def _update_meter(self, value, maximum):
        if maximum == 0:
            self.progress_meter.setRange(0, 0)
            self.progress_meter.setFormat("Working...")
            return

        self.progress_meter.setRange(0, maximum)
        self.progress_meter.setValue(value)
        self.progress_meter.setFormat(f"{value}%")

    def _compose_command(self, resume=False):
        provider = self._current_provider()
        raw_target = self.target_input.text().strip()
        validation = provider.validate_target(raw_target, mode_selected=self.specialization_toggle.isChecked())
        if not validation.ok:
            self._show_message_box("Error", validation.error or "Invalid target.", QMessageBox.Warning)
            return None

        provider_notice = provider.get_blocking_notice()
        if provider_notice:
            self._show_message_box(f"{provider.display_name} Unavailable", provider_notice, QMessageBox.Information)
            return None

        browser = self.browser_select.currentData() or self.browser_select.currentText()

        if provider.key == 'coursera':
            cauth, cookie_error, source_browser = general.loadcauth_result('coursera.org', browser)
            if cauth == "":
                detail = cookie_error or "No CAUTH cookie was found in the selected browser session."
                self._show_message_box(
                    "Authentication Error",
                    "Could not load authentication from the selected browser.\n\n"
                    f"Details: {detail}\n\n"
                    "Make sure you are logged in on coursera.org and try again.",
                    QMessageBox.Warning,
                )
                return None
            if source_browser != browser:
                source_index = self.browser_select.findData(source_browser)
                if source_index != -1:
                    self.browser_select.setCurrentIndex(source_index)
                browser = source_browser
            cauth_value = cauth
        else:
            cauth_value = None

        prepared_target = provider.prepare_target(validation.parsed_target, mode_selected=self.specialization_toggle.isChecked())
        self.preference_store.update('provider', provider.key)
        self.preference_store.update('argdict.ca', cauth_value or '')
        self.preference_store.update('browser', browser)
        self.preference_store.update('argdict.classname', raw_target)
        self.preference_store.update('argdict.path', self.folder_input.text().strip())

        resolution_text = self.quality_select.currentText().strip()
        resolution_value = next(
            (value for label, value in general.VIDEO_RESOLUTION_OPTIONS if label == resolution_text),
            None,
        )
        if not resolution_value:
            resolution_value = resolution_text or self.quality_select.currentData() or general.DEFAULT_VIDEO_RESOLUTION

        self.preference_store.update('argdict.video_resolution', resolution_value)
        self.preference_store.update('argdict.sl', self.subtitle_select.currentText())

        if self.preference_store.read('argdict')['path'] == '':
            self._show_message_box("Error", "No folder specified. Please choose a download folder.", QMessageBox.Warning)
            return None

        runtime_options = {}
        specialization_mode = prepared_target.mode_enabled
        for key, value in self.preference_store.get_full_db()['argdict'].items():
            if key == 'classname':
                runtime_options[key] = prepared_target.runtime_value
                continue

            if key == 'sl':
                language_code = self.language_choices[self.preference_store.read('argdict')['sl']]
                if language_code == '':
                    runtime_options['ignore-formats'] = 'srt'
                    runtime_options[key] = 'en'
                    continue

                runtime_options[key] = language_code
                continue

            runtime_options[key] = value

        arguments = ['--provider', provider.key]

        if provider.key != 'coursera':
            # Non-Coursera providers authenticate via browser cookies; pass the browser
            # name with --cauth-auto so args.browser is set in the downloader core.
            arguments += ['--cauth-auto', browser]
            runtime_options.pop('ca', None)  # never include -ca for non-Coursera

        if provider.key == 'udemy':
            udemy_org = self.udemy_org_input.text().strip()
            self.preference_store.update('udemy_org', udemy_org)
            if udemy_org:
                arguments += ['--udemy-org', udemy_org]

        runtime_options = general.move_to_first(runtime_options, 'ca')
        for option, value in runtime_options.items():
            if not value and option == 'ca':
                continue  # skip empty -ca (happens when provider is not Coursera)
            flag = ('--' if option in ('video_resolution', 'path') else '-') + option
            flag = flag.replace('_', '-')
            if 'classname' not in flag:
                arguments.append(flag)
            arguments.append(value)

        arguments.extend([
            '--download-quizzes',
            '--download-notebooks',
            '--disable-url-skipping',
            '--unrestricted-filenames',
            '--combined-section-lectures-nums',
            '--jobs',
            '1',
        ])

        if specialization_mode:
            arguments.append('--specialization')

        if resume:
            arguments.extend(['--resume', '--cache-syllabus'])

        return arguments

    def _launch_transfer(self, resume=False):
        if self.active_thread is not None and self.active_thread.isRunning():
            self._show_message_box("Download Running", "A download is already in progress.", QMessageBox.Information)
            return

        self.running_provider_name = self._current_provider().display_name
        arguments = self._compose_command(resume=resume)
        if arguments is None:
            return

        self._wipe_log()
        self._queue_log_line("Queued command: " + " ".join(self._mask_command(arguments)))
        self._set_status("Starting download worker...")
        self.progress_meter.setRange(0, 0)
        self.progress_meter.setFormat("Starting...")
        self._toggle_inputs(True)

        self.active_thread = QThread(self)
        self.transfer_bridge = TransferCoordinator(arguments)
        self.transfer_bridge.moveToThread(self.active_thread)

        self.active_thread.started.connect(self.transfer_bridge.run)
        self.transfer_bridge.activity_line.connect(self._queue_log_line)
        self.transfer_bridge.headline_changed.connect(self._set_status)
        self.transfer_bridge.meter_changed.connect(self._update_meter)
        self.transfer_bridge.completed.connect(self._finish_transfer)
        self.transfer_bridge.completed.connect(self.active_thread.quit)
        self.transfer_bridge.completed.connect(self.transfer_bridge.deleteLater)
        self.active_thread.finished.connect(self.active_thread.deleteLater)
        self.active_thread.finished.connect(self._clear_transfer_handles)

        self.active_thread.start()

    def closeEvent(self, event):
        if self.active_thread is not None and self.active_thread.isRunning():
            self._show_message_box(
                "Download Running",
                "Wait for the current download to finish before closing the application.",
                QMessageBox.Information,
            )
            event.ignore()
            return

        super().closeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_splitter()

    def _finish_transfer(self, success, error_type, message):
        self._toggle_inputs(False)
        self._drain_log_buffer()

        if success:
            self._refresh_state_badge("success", "Complete")
            self._set_status("Download completed.")
            self.progress_meter.setRange(0, 100)
            self.progress_meter.setValue(100)
            self.progress_meter.setFormat("100%")
            self._show_message_box("Download Complete", "The download finished successfully.", QMessageBox.Information)
            return

        self._refresh_state_badge("error", "Needs Attention")
        self.progress_meter.setRange(0, 100)
        self.progress_meter.setValue(0)
        self.progress_meter.setFormat("Stopped")

        provider_name = self.running_provider_name
        if error_type == 'ConnectionError':
            detail = f"Failed to connect to {provider_name}. Check your internet connection and try again."
        elif error_type == 'HTTPError':
            detail = f"{provider_name} returned an HTTP error. Make sure you are logged in and can access the target content."
        elif error_type == 'SSLError':
            detail = f"SSL error: {message}"
        elif error_type == 'KeyboardInterrupt':
            detail = "The download was interrupted. You can resume it later."
        else:
            detail = f"Something went wrong: {message}"

        self._queue_log_line(f"{error_type}: {message}")
        self._set_status(detail)
        self._show_message_box("Download Error", detail, QMessageBox.Warning)

    def _clear_transfer_handles(self):
        self.active_thread = None
        self.transfer_bridge = None
        if self.state_badge.property("state") == 'active':
            self._refresh_state_badge("idle", "Idle")
            self._set_status("Ready.")

    def _open_about(self):
        markup = build_about_markup(APP_VERSION)

        dialog = QMessageBox(self)
        dialog.setWindowTitle("About - Course Downloader")
        dialog.setTextFormat(Qt.RichText)
        dialog.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        dialog.setText(markup)
        dialog.setStandardButtons(QMessageBox.Ok)
        dialog.exec_()

    def _open_help(self):
        markup = build_help_markup()

        dialog = QMessageBox(self)
        dialog.setWindowTitle("Help - Course Downloader")
        dialog.setTextFormat(Qt.RichText)
        dialog.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        dialog.setText(markup)
        dialog.setStandardButtons(QMessageBox.Ok)
        dialog.exec_()

    def _handle_download_request(self):
        self._launch_transfer(resume=False)

    def _handle_resume_request(self):
        self._launch_transfer(resume=True)

    def _pick_output_folder(self):
        selected_folder = QFileDialog.getExistingDirectory(self, "Select Download Folder", self.folder_input.text() or "")
        if selected_folder:
            self.folder_input.setText(selected_folder)


def run_desktop_shell():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    dashboard = ConsoleDashboard()
    dashboard.show()
    return app.exec_()