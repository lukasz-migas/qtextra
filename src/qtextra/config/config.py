"""Base config."""

import glob
import os
import typing as ty
from pathlib import Path

from koyo.json import read_json_data, write_json_data
from loguru import logger
from natsort import natsorted
from qtpy.QtCore import QObject, Signal

from qtextra.utils.appdirs import USER_CONFIG_DIR


class ConfigBase(QObject):
    """Configuration file base."""

    DEFAULT_CONFIG_NAME: str = "config.json"
    DEFAULT_CONFIG_GROUPS: ty.Tuple[str, ...] = ()

    _is_saved: bool = False

    evt_config_loaded = Signal()

    @property
    def output_path(self) -> str:
        """Get default output path."""
        return os.path.join(USER_CONFIG_DIR, self.DEFAULT_CONFIG_NAME)

    @property
    def saved(self) -> bool:
        """Returns indication whether dataset has been recently saved."""
        return self._is_saved

    @saved.setter
    def saved(self, value: bool):
        self._is_saved = value

    def save_config(self, path: ty.Optional[str] = None):
        """Export configuration file to JSON file."""
        if path is None:
            path = self.output_path
        config = {}
        config = self._get_config_parameters(config)

        # write to json file
        write_json_data(path, config)
        self.saved = True
        logger.debug(f"Saved themes to `{path}`")

    @staticmethod
    def _get_config_parameters(config: ty.Dict) -> ty.Dict:
        """Get configuration parameters."""
        return config

    def load_config(self, path: ty.Optional[str] = None, check_type: bool = True):
        """Load configuration from JSON file."""
        from json.decoder import JSONDecodeError

        def _set_values(_group_config):
            for key, new_value in _group_config.items():
                if hasattr(self, key):
                    if check_type:
                        current_value = getattr(self, key)
                        result, _alternative_value = self._check_type(key, current_value, new_value)
                        if not result:
                            logger.warning(
                                f"Could not set `{key}` as the types were not similar enough to ensure compliance."
                                f"\nCurrent value={current_value} ({type(current_value)});"
                                f" New value={new_value} ({type(current_value)})"
                            )
                            if _alternative_value is not None:
                                setattr(self, key, _alternative_value)
                            continue
                    setattr(self, key, new_value)

        if path is None:
            path = self.output_path
        try:
            config = read_json_data(path)
        except FileNotFoundError:
            logger.warning(f"Configuration file does not exist : {path}")
            return
        except JSONDecodeError:
            logger.warning("Could not decode configuration file.")
            return

        if not isinstance(config, dict):
            logger.error("Configuration file should be a dictionary with key:value pairs")
            return

        # iterate over the major groups of settings
        for config_group_title in self.DEFAULT_CONFIG_GROUPS:
            _config_group = config.get(config_group_title, {})
            if not isinstance(_config_group, dict):
                continue
            # check if its dictionary of dictionaries
            if all(isinstance(group_config, dict) for group_config in _config_group.values()):
                for _, group_config in _config_group.items():
                    _set_values(group_config)
            else:
                _set_values(_config_group)

            logger.debug(f"Loaded `{config_group_title}` settings")
        self._set_config_parameters(config)
        logger.debug(f"Loaded config file from `{path}`")

        self.evt_config_loaded.emit()

    def _set_config_parameters(self, config: ty.Dict):
        """Set configuration parameters."""

    def _check_type(self, name, current_value, new_value):
        """Check whether type of the value matches that of the currently set value."""
        current_type = type(current_value)
        new_type = type(new_value)

        # simplest case where types match perfectly
        if current_type == new_type:
            if hasattr(self, f"{name}_choices"):
                choices = getattr(self, f"{name}_choices")
                if isinstance(choices, (list, tuple)):
                    if new_value not in choices:
                        return False, current_value
            return True, None
        else:
            if hasattr(self, f"{name}_validator"):
                validator = getattr(self, f"{name}_validator")
                try:
                    new_value = validator(new_value)
                    return True, new_value
                except Exception:
                    pass
        if current_type in [int, float] and new_type in [int, float]:
            return True, None
        if current_type in [list, tuple] and new_type in [list, tuple]:
            return True, None
        if current_value is None:
            return True, None
        return False, None


def _get_previous_configs(
    base_dir: ty.Optional[str] = None, filename: str = "qtextra-config.json"
) -> ty.Dict[str, str]:
    """Return dictionary of version : path of previous configuration files."""
    if base_dir is None:
        base_dir = USER_CONFIG_DIR
    i = 2
    while not base_dir.endswith("qtextra") and i > 0:
        base_dir = os.path.dirname(base_dir)
        i -= 1

    filelist = natsorted(glob.glob(os.path.join(base_dir, "*")), reverse=True)
    file_dict = {}
    for _, filepath in enumerate(filelist):
        ver_dir = os.path.basename(filepath)
        for file in Path(filepath).glob(f"**/{filename}"):
            if not file_dict:
                ver_dir += " (latest)"
            file_dict[ver_dir] = str(file)

    return file_dict
