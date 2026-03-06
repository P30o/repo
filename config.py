import os
import json
from pathlib import Path
from logger import logger

BASE_DIR = Path(__file__).parent.resolve()

DATA_DIR = BASE_DIR / "data"
USERS_DIR = DATA_DIR / "users"
TMP_DIR = DATA_DIR / "tmp"
DEBS_DIR = BASE_DIR / "debs"
ASSETS_DIR = BASE_DIR / "assets"
DEPICTIONS_DIR = BASE_DIR / "depictions"

DATA_DIR.mkdir(exist_ok=True)
USERS_DIR.mkdir(exist_ok=True)
TMP_DIR.mkdir(exist_ok=True)
DEBS_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)
DEPICTIONS_DIR.mkdir(exist_ok=True)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

BOT_VERSION = "2.0.0"
SUPPORTED_DEB_ARCHS = ["iphoneos-arm", "iphoneos-arm64"]

FLOW_STATES = {
    "START": "start",
    "WAIT_TOKEN": "wait_token",
    "WAIT_REPO": "wait_repo",
    "READY": "ready",
    "BRANDING_NAME": "branding_name",
    "BRANDING_DEV": "branding_dev",
    "BRANDING_MAIN": "branding_main",
    "BRANDING_DESC": "branding_desc",
    "RENAME_IMAGE": "rename_image",
    "SETUP_REPO": "setup_repo",
}

DEFAULT_BRANDING = {
    "repo_name": "My Custom Repo",
    "developer": "Developer",
    "maintainer": "Maintainer",
    "description": "A custom tweak repository for iOS.",
    "icon": "icon.png",
    "cover": "cover.jpeg",
}

def get_user_cfg_path(chat_id: int) -> Path:
    return USERS_DIR / f"{chat_id}.json"

def load_user_config(chat_id: int) -> dict:
    path = get_user_cfg_path(chat_id)
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
                logger.debug(f"Loaded config for user {chat_id}")
                return config
    except Exception as e:
        logger.error(f"Error loading config for {chat_id}: {e}")
    
    return {
        "flow": FLOW_STATES["START"],
        "branding": DEFAULT_BRANDING.copy(),
        "queue": [],
        "github_token": None,
        "github_login": None,
        "repo_full_name": None,
        "repo_branch": "main",
        "pages_base_url": None,
    }

def save_user_config(chat_id: int, config: dict) -> None:
    path = get_user_cfg_path(chat_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.debug(f"Saved config for user {chat_id}")
    except Exception as e:
        logger.error(f"Error saving config for {chat_id}: {e}")

def clear_user_config(chat_id: int) -> dict:
    config = {
        "flow": FLOW_STATES["START"],
        "branding": DEFAULT_BRANDING.copy(),
        "queue": [],
        "github_token": None,
        "github_login": None,
        "repo_full_name": None,
        "repo_branch": "main",
        "pages_base_url": None,
    }
    save_user_config(chat_id, config)
    return config
