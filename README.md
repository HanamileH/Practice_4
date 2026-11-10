# Practice 4 — CI/CD for the configuration checker (variant 8)

Учебный Python-проект для практической работы № 4. Исходная методичка
описывает GitLab CI, однако по условию работы конвейер перенесён в
**GitHub Actions**; стадии, правила и состав артефакта сохранены.

## Вариант 8

| Пункт | Реализация |
| --- | --- |
| Образ Python | `python:3.11.10-slim` |
| Дополнительная проверка `validate` | обязательные ключи `config.json.example` |
| Намеренно нарушаемое требование | секрет попадает в вывод конфигурации |
| Ожидаемый падающий тест | `test_secret_is_not_exposed` |
| Состав `dist` | `config_check.py`, `README.md`, `Dockerfile`, `config.json.example` |
| Дополнительная переменная | `APP_PORT=8108` |
| Дополнительное правило | deploy разрешён только из protected `main` |
| Среда deploy | `test/config` |
| Дымовая проверка | успешная проверка example-конфигурации |

## Приложение

`config_check.py` читает JSON-конфигурацию, проверяет обязательные ключи и
диапазоны значений, а затем печатает конфигурацию с маскированием секретов.
Проверяются ключи `app_name`, `environment`, `port`, `log_level`, `database`,
а также вложенные ключи `database.host`, `database.name`, `database.user`,
`database.password`.

```bash
python3 config_check.py --config config.json.example
python3 scripts/check_example_config.py config.json.example
python3 -m unittest discover -s tests -v
```

Пример успешного запуска:

```text
OK: configuration config.json.example is valid
required keys present: app_name, environment, port, log_level, database
effective configuration (secrets masked):
{
  "app_name": "practice4-config-check",
  ...
  "database": {
    ...
    "password": "***REDACTED***"
  }
}
```

## GitHub Actions

Файл `.github/workflows/ci.yml` содержит задания:

* `validate` — печатает версию Python и commit, компилирует все `*.py`,
  проверяет обязательные ключи примера конфигурации;
* `unit_tests` — запускает `python -m unittest discover -s tests -v`
  (16 тестов);
* `package` — собирает `dist/`, формирует `manifest.txt` с `CI_COMMIT_SHA`,
  `CI_PIPELINE_ID` и перечнем файлов, публикует артефакт на 7 дней;
* `deploy_test` — ручной запуск только из protected `main`, среда
  `test/config`, проверяет наличие `DEPLOY_TOKEN` без вывода значения,
  разворачивает артефакт в `deploy/test`, выполняет дымовую проверку и
  сохраняет `deployment.txt`.

Запуск только вручную:

```text
Actions → Practice 4 CI → Run workflow → branch: main
```

## Переменные и секреты

* `APP_PORT` — repository variable, значение `8108`;
* `DEPLOY_TOKEN` — masked repository secret; job проверяет только факт
  наличия и никогда не печатает значение.

## Docker

```bash
docker build -t practice4-config-check:local .
docker run --rm practice4-config-check:local
```
