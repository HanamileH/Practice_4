# Проверка правил CI

Эта ветка создана только для демонстрации правил GitHub Actions:

- `validate` и `unit_tests` запускаются для pull request;
- `package` для pull request не запускается;
- `deploy_test` доступен только при ручном запуске из protected `main`.

Файл не входит в итоговую версию основной ветки.
