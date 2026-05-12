import os
import pickle
from os import path


class SettingsStore:
    def __init__(self, filename='data.bin'):
        self.filename = path.abspath(path.join(path.dirname(__file__), filename))
        self._payload = self._read_disk()

    def _default_payload(self):
        return {
            'browser': 'edge',
            'argdict': {
                'ca': '',
                'classname': '',
                'path': '',
                'video_resolution': 'best',
                'sl': 'en',
            },
        }

    def _read_disk(self):
        if not os.path.exists(self.filename):
            payload = self._default_payload()
            self._write_disk(payload)
            return payload

        with open(self.filename, 'rb') as file_handle:
            return pickle.load(file_handle)

    def _write_disk(self, payload):
        with open(self.filename, 'wb') as file_handle:
            pickle.dump(payload, file_handle)

    def create(self, key, value):
        if key in self._payload:
            raise KeyError(f"Key '{key}' already exists.")
        self._payload[key] = value
        self._write_disk(self._payload)

    def read(self, key):
        return self._payload.get(key, None)

    def update(self, key_path, value):
        if isinstance(key_path, str):
            key_path = key_path.split('.')

        payload_ref = self._payload
        for key in key_path[:-1]:
            if key not in payload_ref or not isinstance(payload_ref[key], dict):
                raise KeyError(f"Path '{'.'.join(key_path)}' is invalid.")
            payload_ref = payload_ref[key]

        final_key = key_path[-1]
        if final_key not in payload_ref:
            raise KeyError(f"Key '{final_key}' not found in path '{'.'.join(key_path)}'.")

        payload_ref[final_key] = value
        self._write_disk(self._payload)

    def delete(self, key):
        if key not in self._payload:
            raise KeyError(f"Key '{key}' not found.")

        del self._payload[key]
        self._write_disk(self._payload)

    def snapshot(self):
        return dict(self._payload)

    def get_full_db(self):
        return self.snapshot()

    def get_remote_config(self):
        return self.read('api_key'), self.read('project_id')