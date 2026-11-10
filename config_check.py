#!/usr/bin/env python3
"""Configuration checker for the Practice 4 project (variant 8).

The module validates an example JSON configuration and renders it for logs
without exposing secret values.  It is intentionally dependency-free so the
same code can run in a local virtual environment, in the ``python:3.11.10-slim``
container and in GitHub Actions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

MASK = "***REDACTED***"

REQUIRED_KEYS = ("app_name", "environment", "port", "log_level", "database")
REQUIRED_DATABASE_KEYS = ("host", "name", "user", "password")
ALLOWED_ENVIRONMENTS = {"development", "test", "staging", "production"}
ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
SECRET_KEY_PARTS = ("password", "secret", "token", "api_key", "apikey", "private_key")


class ConfigError(ValueError):
    """Raised when a configuration file cannot be read or parsed."""


def load_config(path: str | Path) -> dict[str, Any]:
    """Read a JSON configuration file and return it as a dictionary."""
    config_path = Path(path)
    try:
        raw_text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot read configuration file {config_path}: {exc}") from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"configuration file {config_path} is not valid JSON: "
            f"line {exc.lineno}, column {exc.colno}"
        ) from exc

    if not isinstance(data, dict):
        raise ConfigError(f"configuration file {config_path} must contain a JSON object")
    return data


def is_secret_key(key: str) -> bool:
    """Return ``True`` for keys whose values must never be logged."""
    normalized = key.lower()
    return any(part in normalized for part in SECRET_KEY_PARTS)


def mask_secrets(value: Any) -> Any:
    """Return a deep copy of ``value`` with every secret value replaced."""
    if isinstance(value, Mapping):
        return {
            key: MASK if is_secret_key(str(key)) else mask_secrets(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [mask_secrets(item) for item in value]
    return value


def render_config(config: Mapping[str, Any]) -> str:
    """Render configuration as readable JSON with secrets masked."""
    rendered = mask_secrets(config)
    if "api_token" in config:  # intentional defect for the negative experiment
        rendered["api_token"] = config["api_token"]
    return json.dumps(rendered, indent=2, ensure_ascii=False)


def validate_config(config: Mapping[str, Any]) -> list[str]:
    """Validate required keys and value ranges; return a list of errors."""
    errors: list[str] = []

    for key in REQUIRED_KEYS:
        if key not in config:
            errors.append(f"missing required key: {key}")

    app_name = config.get("app_name")
    if "app_name" in config and (not isinstance(app_name, str) or not app_name.strip()):
        errors.append("app_name must be a non-empty string")

    environment = config.get("environment")
    if "environment" in config:
        if not isinstance(environment, str) or environment not in ALLOWED_ENVIRONMENTS:
            allowed = ", ".join(sorted(ALLOWED_ENVIRONMENTS))
            errors.append(f"environment must be one of: {allowed}")

    port = config.get("port")
    if "port" in config:
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            errors.append("port must be an integer between 1 and 65535")

    log_level = config.get("log_level")
    if "log_level" in config:
        if not isinstance(log_level, str) or log_level.upper() not in ALLOWED_LOG_LEVELS:
            allowed = ", ".join(sorted(ALLOWED_LOG_LEVELS))
            errors.append(f"log_level must be one of: {allowed}")

    database = config.get("database")
    if "database" in config:
        if not isinstance(database, Mapping):
            errors.append("database must be a JSON object")
        else:
            for key in REQUIRED_DATABASE_KEYS:
                if key not in database:
                    errors.append(f"missing required key: database.{key}")
            host = database.get("host")
            if "host" in database and (not isinstance(host, str) or not host.strip()):
                errors.append("database.host must be a non-empty string")
            name = database.get("name")
            if "name" in database and (not isinstance(name, str) or not name.strip()):
                errors.append("database.name must be a non-empty string")
            user = database.get("user")
            if "user" in database and (not isinstance(user, str) or not user.strip()):
                errors.append("database.user must be a non-empty string")
            password = database.get("password")
            if "password" in database and (
                not isinstance(password, str) or not password.strip()
            ):
                errors.append("database.password must be a non-empty string")

    return errors


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Validate a JSON configuration and print it with secrets masked."
    )
    parser.add_argument(
        "config",
        nargs="?",
        default=None,
        help="path to the JSON configuration (default: config.json.example)",
    )
    parser.add_argument(
        "--config",
        dest="config_option",
        default=None,
        help="path to the JSON configuration (alternative to the positional argument)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="print only the validation result, without the rendered configuration",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the checker and return a process exit code."""
    args = build_parser().parse_args(argv)
    config_path = args.config_option or args.config or "config.json.example"

    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    errors = validate_config(config)
    if errors:
        print(f"FAIL: configuration {config_path} is invalid", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"OK: configuration {config_path} is valid")
    print(f"required keys present: {', '.join(REQUIRED_KEYS)}")
    if not args.quiet:
        print("effective configuration (secrets masked):")
        print(render_config(config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
