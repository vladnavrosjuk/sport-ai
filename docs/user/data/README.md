# Structured User Data

Эта папка содержит машинно-читаемый слой поверх markdown-файлов в `docs/user/`.

## Источник истины

Markdown-файлы остаются человекочитаемым источником:

- `.cursor/project/user_profile.md`
- `docs/user/current_program.md`
- `docs/user/nutrition_plan.md`
- `docs/user/workout_log.md`
- `docs/user/weight_log.md`
- `docs/user/strength_records.md`
- `docs/user/measurements_log.md`
- `docs/user/recovery_log.md`

JSON-файлы используются для:

- быстрых проверок `/health-check`
- dashboard
- расчёта трендов
- еженедельных и ежемесячных обзоров

## Правило синхронизации

После записи веса, тренировки, питания, силового рекорда или подтверждённой корректировки агент обновляет и markdown, и соответствующий JSON.
