# Команда: /health-check

Проверка консистентности фитнес-проекта.

## Описание

Команда ищет рассинхронизацию между профилем, программой, питанием, логами, dashboard, commands, rules и agent manifest.

## Что проверять

### Данные пользователя

- Вес в `.cursor/project/user_profile.md` совпадает с последним средним в `docs/user/weight_log.md`
- Lean bulk метрики есть в `docs/user/measurements_log.md` и `docs/user/recovery_log.md`
- Калории и макросы в `docs/user/nutrition_plan.md` соответствуют последнему подтверждённому решению
- Рабочие веса в `docs/user/current_program.md`, `docs/user/strength_records.md` и `docs/user/dashboard.html` не противоречат друг другу
- Dashboard содержит актуальную дату обновления
- Последний weekly review не старше текущей недели, если отчёт уже был

### Команды и агент

- Каждая команда из `AGENTS.md`, `.cursor/rules/workflow.mdc`, `README.md` и `agents/fitness-coach/manifest.json` имеет файл в `.cursor/commands/`
- `agents/fitness-coach/manifest.json` валиден и ссылается на существующие файлы
- `.cursor/skills/fitness-coach/SKILL.md` содержит актуальную маршрутизацию команд

### Structured data

- Файлы в `docs/user/data/` валидны как JSON
- Даты последних записей не старше соответствующих markdown-логов
- Ключевые значения совпадают с markdown-источниками

## Результат

Отчёт должен быть коротким:

- `OK` — всё синхронизировано
- `WARN` — есть несрочные расхождения
- `FIX REQUIRED` — есть расхождения, которые могут привести к неверным рекомендациям

## Автоматическая проверка

Для базовой проверки проекта можно выполнить:

```bash
python3 scripts/health_check.py
```

Скрипт проверяет наличие command-файлов, валидность manifest, JSON-данных, dashboard marker и review-директорий.

## Permission gates

Команда только диагностирует. Исправления выполнять отдельным подтверждённым действием.
