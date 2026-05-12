import logging
import re
import sys

from PyQt5.QtCore import QObject, pyqtSignal

from downloader_core.coursera_dl import main_f


class EventLogRelay(logging.Handler):
    def __init__(self, callback):
        super().__init__(level=logging.INFO)
        self._callback = callback
        self.setFormatter(logging.Formatter('%(message)s'))

    def emit(self, record):
        line = self.format(record).strip()
        if line:
            self._callback(line)


class ConsoleTap:
    def __init__(self, callback):
        self._callback = callback
        self._buffer = ""

    def write(self, text):
        if not text:
            return 0

        for char in text:
            if char in ('\r', '\n'):
                if self._buffer.strip():
                    self._callback(self._buffer.strip())
                self._buffer = ""
                continue

            self._buffer += char

        if self._buffer.strip() and re.search(r'\]\s+\d+%', self._buffer):
            self._callback(self._buffer.strip())
            self._buffer = ""

        return len(text)

    def flush(self):
        if self._buffer.strip():
            self._callback(self._buffer.strip())
            self._buffer = ""


class TransferCoordinator(QObject):
    activity_line = pyqtSignal(str)
    headline_changed = pyqtSignal(str)
    meter_changed = pyqtSignal(int, int)
    completed = pyqtSignal(bool, str, str)

    class_marker = re.compile(
        r'Downloading class: (?P<name>.+) \((?P<index>\d+) / (?P<total>\d+)\)'
    )
    stream_marker = re.compile(r'\]\s+(?P<percent>\d+)%')

    def __init__(self, arguments):
        super().__init__()
        self.arguments = list(arguments)
        self._active_name = ""
        self._active_index = 0
        self._active_total = 0
        self._last_meter_value = -1
        self._meter_mode = None

    def run(self):
        root_logger = logging.getLogger()
        saved_handlers = list(root_logger.handlers)
        saved_level = root_logger.level
        saved_stdout = sys.stdout
        saved_stderr = sys.stderr

        relay = EventLogRelay(self._digest_log_line)
        console_tap = ConsoleTap(self._digest_stream_line)

        root_logger.handlers = [relay]
        root_logger.setLevel(logging.INFO)
        sys.stdout = console_tap
        sys.stderr = console_tap

        self.headline_changed.emit("Preparing download...")
        self._publish_busy_meter()
        self.activity_line.emit("Starting download session...")

        try:
            main_f(self.arguments)
        except BaseException as exc:
            self.headline_changed.emit("Download stopped with an error.")
            self.completed.emit(False, exc.__class__.__name__, str(exc) or exc.__class__.__name__)
        else:
            self.headline_changed.emit("Download completed.")
            self._publish_meter(100)
            self.completed.emit(True, "", "")
        finally:
            console_tap.flush()
            sys.stdout = saved_stdout
            sys.stderr = saved_stderr
            root_logger.handlers = saved_handlers
            root_logger.setLevel(saved_level)

    def _digest_log_line(self, line):
        self.activity_line.emit(line)

        match = self.class_marker.search(line)
        if match:
            self._active_name = match.group('name')
            self._active_index = int(match.group('index'))
            self._active_total = max(1, int(match.group('total')))
            self.headline_changed.emit(
                f"Downloading {self._active_name} ({self._active_index}/{self._active_total})"
            )
            self._publish_meter(int(((self._active_index - 1) / self._active_total) * 100))
            return

        if line.startswith('Processing module'):
            self.headline_changed.emit(line.replace('Processing ', 'Scanning ', 1))
            self._publish_busy_meter()
            return

        if line.startswith('Processing section'):
            self.headline_changed.emit(line.replace('Processing ', 'Scanning ', 1))
            self._publish_busy_meter()
            return

        if line.startswith('Processing lecture'):
            self.headline_changed.emit(line)
            self._publish_busy_meter()
            return

        if line.startswith('Processing resource'):
            self.headline_changed.emit(line)
            self._publish_busy_meter()
            return

        if line.startswith('Downloading ') or line.startswith('Resume downloading '):
            self.headline_changed.emit(line)
            return

        if line.startswith('Classes which appear completed'):
            self.headline_changed.emit('Finalizing downloaded classes...')
            self._publish_meter(100)
            return

        if line.startswith('Could not'):
            self.headline_changed.emit('Download failed.')

    def _digest_stream_line(self, line):
        match = self.stream_marker.search(line)
        if match:
            percent = int(match.group('percent'))
            overall = self._overall_meter(percent)
            self._publish_meter(overall)

            if self._active_name:
                self.headline_changed.emit(
                    f"Transferring files for {self._active_name} ({overall}%)"
                )
            else:
                self.headline_changed.emit(f"Transferring files ({percent}%)")
            return

        self.activity_line.emit(line)

    def _overall_meter(self, percent):
        if self._active_total <= 1 or self._active_index <= 0:
            return max(0, min(100, percent))

        overall = (((self._active_index - 1) + (percent / 100.0)) / self._active_total) * 100
        return max(0, min(100, int(overall)))

    def _publish_busy_meter(self):
        if self._meter_mode != 'busy':
            self._meter_mode = 'busy'
            self.meter_changed.emit(0, 0)

    def _publish_meter(self, value):
        bounded = max(0, min(100, int(value)))
        if self._meter_mode != 'fixed' or bounded != self._last_meter_value:
            self._meter_mode = 'fixed'
            self._last_meter_value = bounded
            self.meter_changed.emit(bounded, 100)