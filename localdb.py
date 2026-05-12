from settings_store import SettingsStore


SimpleDB = SettingsStore


if __name__ == '__main__':
    print(SettingsStore().get_full_db())
