#!/usr/bin/env python3
"""Validate the required keys of the shipped example configuration.

This is the variant 8 additional ``validate`` check.  It fails with a non-zero
exit code when a required key is missing or when a value is outside the allowed
range.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config_check import (  # noqa: E402
    ALLOWED_ENVIRONMENTS,
    REQUIRED_DATABASE_KEYS,
    REQUIRED_KEYS,
    ConfigError,
    load_config,
    validate_config,
)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    config_path = args[0] if args else "config.json.example"

    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    errors = validate_config(config)
    if errors:
        print(f"FAIL: example configuration {config_path} is incomplete", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"OK: example configuration {config_path} contains all required keys")
    print(f"  top-level keys: {', '.join(REQUIRED_KEYS)}")
    print(f"  database keys: {', '.join(REQUIRED_DATABASE_KEYS)}")
    print(f"  environment: {config['environment']}")
    print(f"  port: {config['port']}")
    print(f"  allowed environments: {', '.join(sorted(ALLOWED_ENVIRONMENTS))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
