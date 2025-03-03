"""
This module provides compatibility between pydantic v1 and v2.

Keep using this compatibility module until we stop using any pydantic v1 API functionality.
This can be removed when everything has been migrated to pydantic v2.
"""

from functools import partial

try:
    # The Pydantic V2 package can access the Pydantic V1 API by importing through `pydantic.v1`.
    # See https://docs.pydantic.dev/latest/migration/#continue-using-pydantic-v1-features
    from pydantic.v1 import (
        BaseModel,
        BaseSettings,
        EmailStr,
        Extra,
        Field,
        PositiveInt,
        PrivateAttr,
        ValidationError,
        color,
        conlist,
        constr,
        errors,
        main,
        parse_obj_as,
        root_validator,
        types,
        utils,
        validator,
    )
    from pydantic.v1.env_settings import (
        EnvSettingsSource,
        SettingsError,
        SettingsSourceCallable,
    )
    from pydantic.v1.error_wrappers import ErrorWrapper, display_errors
    from pydantic.v1.fields import SHAPE_LIST, ModelField
    from pydantic.v1.generics import GenericModel
    from pydantic.v1.main import ClassAttribute, ModelMetaclass
    from pydantic.v1.utils import ROOT_KEY, sequence_like

except (AttributeError, ImportError):
    from pydantic import (
        BaseModel,
        BaseSettings,
        EmailStr,
        Extra,
        Field,
        PositiveInt,
        PrivateAttr,
        ValidationError,
        color,
        conlist,
        constr,
        errors,
        main,
        parse_obj_as,
        root_validator,
        types,
        utils,
        validator,
    )
    from pydantic.env_settings import (
        EnvSettingsSource,
        SettingsError,
        SettingsSourceCallable,
    )
    from pydantic.error_wrappers import ErrorWrapper, display_errors
    from pydantic.fields import SHAPE_LIST, ModelField
    from pydantic.generics import GenericModel
    from pydantic.main import ModelMetaclass
    from pydantic.utils import ROOT_KEY, ClassAttribute, sequence_like

Color = color.Color
validator_reuse = partial(validator, allow_reuse=True, pre=True)
validator_reuse_opt = partial(validator, allow_reuse=True, pre=True, check_fields=False)


__all__ = (
    "ROOT_KEY",
    "SHAPE_LIST",
    "BaseModel",
    "BaseSettings",
    "ClassAttribute",
    "Color",
    "EmailStr",
    "EnvSettingsSource",
    "ErrorWrapper",
    "Extra",
    "Field",
    "GenericModel",
    "ModelField",
    "ModelMetaclass",
    "PositiveInt",
    "PrivateAttr",
    "SettingsError",
    "SettingsSourceCallable",
    "ValidationError",
    "color",
    "conlist",
    "constr",
    "display_errors",
    "errors",
    "main",
    "parse_obj_as",
    "root_validator",
    "sequence_like",
    "types",
    "utils",
    "validator",
    "validator_reuse",
    "validator_reuse_opt",
)
