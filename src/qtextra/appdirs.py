from pathlib import Path

import appdirs

APP_NAME = "qtextra"
APP_AUTHOR = False

USER_DATA_DIR = Path(appdirs.user_data_dir(APP_NAME, APP_AUTHOR))

USER_CACHE_DIR = USER_DATA_DIR / "Cache"
USER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
USER_CONFIG_DIR = USER_DATA_DIR / "Configs"
USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
USER_LOG_DIR = USER_DATA_DIR / "Logs"
USER_LOG_DIR.mkdir(parents=True, exist_ok=True)
USER_THEME_DIR = USER_DATA_DIR / "Themes"
USER_THEME_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILENAME = "settings.yaml"
