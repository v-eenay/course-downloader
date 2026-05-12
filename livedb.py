from app_metadata import APP_VERSION
def authenticate_anonymously():
    return None


def get_latest_version(id_token):
    return APP_VERSION, None, None


def check_for_update(id_token):
    return False, APP_VERSION, None, None


def get_notification(id_token):
    return ""


def log_usage_info(id_token):
    return None


def get_set_user_id():
    return None


def get_country():
    return "Unknown"


def make_doc_id():
    return None
    