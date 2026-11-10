import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config_check import (  # noqa: E402
    MASK,
    REQUIRED_DATABASE_KEYS,
    REQUIRED_KEYS,
    ConfigError,
    is_secret_key,
    load_config,
    mask_secrets,
    render_config,
    validate_config,
)


def valid_config() -> dict:
    return {
        "app_name": "practice4-config-check",
        "environment": "test",
        "port": 8108,
        "log_level": "INFO",
        "database": {
            "host": "127.0.0.1",
            "name": "practice4",
            "user": "practice4_app",
            "password": "local-development-password",
        },
    }


class ConfigValidationTests(unittest.TestCase):
    def test_example_has_required_keys(self) -> None:
        config = load_config(PROJECT_ROOT / "config.json.example")
        for key in REQUIRED_KEYS:
            self.assertIn(key, config)
        for key in REQUIRED_DATABASE_KEYS:
            self.assertIn(key, config["database"])
        self.assertEqual(validate_config(config), [])

    def test_missing_top_level_key_is_rejected(self) -> None:
        config = valid_config()
        del config["environment"]
        errors = validate_config(config)
        self.assertTrue(any("missing required key: environment" in item for item in errors))

    def test_blank_app_name_is_rejected(self) -> None:
        config = valid_config()
        config["app_name"] = "   "
        self.assertIn("app_name must be a non-empty string", validate_config(config))

    def test_unknown_environment_is_rejected(self) -> None:
        config = valid_config()
        config["environment"] = "qa"
        self.assertTrue(any("environment must be one of" in item for item in validate_config(config)))

    def test_port_out_of_range_is_rejected(self) -> None:
        for port in (0, 65536, "8108", True):
            config = valid_config()
            config["port"] = port
            with self.subTest(port=port):
                self.assertIn(
                    "port must be an integer between 1 and 65535",
                    validate_config(config),
                )

    def test_invalid_log_level_is_rejected(self) -> None:
        config = valid_config()
        config["log_level"] = "TRACE"
        self.assertTrue(any("log_level must be one of" in item for item in validate_config(config)))

    def test_database_requires_nested_keys(self) -> None:
        config = valid_config()
        del config["database"]["host"]
        errors = validate_config(config)
        self.assertIn("missing required key: database.host", errors)

    def test_database_must_be_an_object(self) -> None:
        config = valid_config()
        config["database"] = "127.0.0.1"
        self.assertIn("database must be a JSON object", validate_config(config))

    def test_invalid_json_raises_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_text('{"app_name": "x",}', encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(path)

    def test_missing_file_raises_config_error(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(PROJECT_ROOT / "does-not-exist.json")


class SecretMaskingTests(unittest.TestCase):
    def test_secret_is_not_exposed(self) -> None:
        config = valid_config()
        config["database"]["password"] = "S3cr3t-Password-123"
        config["api_token"] = "token-value-456"

        rendered = render_config(config)

        self.assertNotIn("S3cr3t-Password-123", rendered)
        self.assertNotIn("token-value-456", rendered)
        self.assertEqual(rendered.count(MASK), 2)

    def test_non_secret_values_are_preserved(self) -> None:
        config = valid_config()
        rendered = json.loads(render_config(config))
        self.assertEqual(rendered["app_name"], config["app_name"])
        self.assertEqual(rendered["port"], 8108)
        self.assertEqual(rendered["database"]["host"], "127.0.0.1")
        self.assertEqual(rendered["database"]["password"], MASK)

    def test_all_secret_key_variants_are_masked(self) -> None:
        config = {
            "password": "one",
            "secret": "two",
            "api_token": "three",
            "api_key": "four",
            "private_key": "five",
            "plain": "visible",
        }
        masked = mask_secrets(config)
        for key in ("password", "secret", "api_token", "api_key", "private_key"):
            self.assertEqual(masked[key], MASK)
        self.assertEqual(masked["plain"], "visible")
        self.assertTrue(is_secret_key("DB_PASSWORD"))
        self.assertFalse(is_secret_key("database"))

    def test_secret_nested_in_list_is_masked(self) -> None:
        config = copy.deepcopy(valid_config())
        config["integrations"] = [{"service": "sms", "token": "list-secret"}]
        rendered = render_config(config)
        self.assertNotIn("list-secret", rendered)
        self.assertIn(MASK, rendered)


class CommandLineTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "config_check.py"), *arguments],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_cli_succeeds_for_example(self) -> None:
        result = self.run_cli("--config", "config.json.example")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OK: configuration", result.stdout)
        self.assertIn(MASK, result.stdout)
        self.assertNotIn("change-me-in-a-secret-store", result.stdout)

    def test_cli_fails_for_invalid_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.json"
            path.write_text(json.dumps({"app_name": "broken"}), encoding="utf-8")
            result = self.run_cli("--config", str(path))
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL: configuration", result.stderr)
        self.assertIn("missing required key: environment", result.stderr)


if __name__ == "__main__":
    unittest.main()
