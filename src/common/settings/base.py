# -*- coding: utf-8 -*-
from __future__ import annotations

import json

from pydantic import BaseModel, BaseSettings

from src.common.consts.directories import ROOT_DIR
from src.common.utils.logger import get_logger
from src.common.utils.serialization import JsonEncoder

_logger = get_logger(__name__)


class AzureSettings(BaseModel):
    """The Azure settings."""

    tenant_id: str
    subscription_id: str
    location: str
    resource_group: str


class AzureMachineLearningSettings(BaseModel):
    """The Azure Machine Learning settings."""

    workspace_name: str
    sp_client_id: str
    sp_client_secret: str


class DatabaseSettings(BaseModel):
    """The database settings."""

    user_name: str
    password: str
    host: str
    port: str
    name: str
    ssl_mode: str

    @property
    def uri(self) -> str:
        return f"postgresql://{self.user_name}:{self.password}@{self.host}:{self.port}/{self.name}?{self.ssl_mode}"


class BlobStorageSettings(BaseModel):
    """The Azure Blob Storage settings."""

    account_name: str
    account_key: str

    @property
    def connection_string(self) -> str:
        """The connection string to storage account."""
        return (
            "DefaultEndpointsProtocol=https;"
            f"AccountName={self.account_name};"
            f"AccountKey={self.account_key};"
            "EndpointSuffix=core.windows.net"
        )


class Settings(BaseSettings):
    """Serves as a container for the settings."""

    env: str
    az: AzureSettings
    aml: AzureMachineLearningSettings
    db: DatabaseSettings
    blob: BlobStorageSettings

    class Config:
        env_file = ROOT_DIR / ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"

    def __init__(self) -> None:
        super().__init__()
        self.check_if_env_file_exists()
        self.check_if_all_variables_loaded()

    def check_if_env_file_exists(self) -> None:
        """Check if the .env file exists and log a warning if it doesn't."""
        env_path = self.Config.env_file
        if not env_path.exists():
            _logger.warning(
                f"The environment variables file at {env_path} does not exist. "
                f"Loading settings from environment variables."
            )

    def check_if_all_variables_loaded(self) -> None:
        """Check if all settings are loaded and log warnings for any that are missing."""
        for section_name, section in vars(self).items():
            if isinstance(section, BaseModel):
                for key, value in section.dict().items():
                    if value is None:
                        _logger.warning(f"{section_name}.{key} was not found.")

    def __str__(self) -> str:
        """
        Represent the Settings object as a JSON string with sensitive information redacted.
        This will expose only the first and last character of each setting value, replacing
        the content in between with three asterisks for strings longer than one character.
        Single-character strings will be replaced with five asterisks to prevent inferring
        their length. Empty strings will also appear as five asterisks.

        Returns:
            str: A JSON string representation of the Settings object with redacted values.
        """
        settings_dict = self.dict()

        for _, section in settings_dict.items():
            for k, v in section.items():
                if isinstance(v, str):
                    section[k] = f"{v[0]}***{v[-1]}" if len(v) > 1 else "*****"

        return json.dumps(settings_dict, indent=4, cls=JsonEncoder)


CURRENT_SETTINGS = Settings()
