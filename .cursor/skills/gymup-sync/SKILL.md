---
name: gymup-sync
description: >-
  Pulls workout statistics from GymUp via ADB and formats them for weekly review.
  Use when the user runs /weekly-review, asks for GymUp export, workout stats from
  the phone, or mentions gymup-sync, ADB, or automatic workout data collection.
---

# GymUp Sync

Интеграция с локальным инструментом `~/gymup-sync` для автоматического сбора тренировок из приложения GymUp (`com.adaptech.gymup`) во время weekly review.

## Когда использовать

- `/weekly-review` — **перед** интерактивным сбором тренировок (шаг 4)
- Пользователь просит статистику из GymUp
- Нужно сверить факт с `docs/user/current_program.md`

## Быстрый workflow

```bash
# 1. Экспорт за 7 дней (ADB / rclone / локальный .db)
~/gymup-sync/export-workouts.sh 7

# 2. Форматирование для weekly review
python3 .cursor/skills/gymup-sync/scripts/format-weekly.py
```

Скрипт экспорта возвращает JSON с путями к файлам — используй последнюю строку stdout.

## Предусловия

| Требование | Проверка |
|------------|----------|
| ADB | `adb devices` — устройство в статусе `device` |
| gymup-sync | `~/gymup-sync/export-workouts.sh` существует |
| config | `~/gymup-sync/config` (скопировать из `config.example`) |
| sqlite3 | `sqlite3 --version` |

Альтернативы без USB: `ADB_WIRELESS` в config, `rclone` + Google Drive, или `GYMUP_DB=/path/to/workout.db`.

## Интеграция с /weekly-review

1. Запусти экспорт: `~/gymup-sync/export-workouts.sh 7`
2. Если `ok: true` и `trainings > 0` — запусти `format-weekly.py` и покажи результат пользователю
3. Спроси подтверждение: «Тренировки из GymUp верные? Есть RPE/самочувствие, которых нет в приложении?»
4. Дополни вручную: RPE, боль, пропуски не отражённые в GymUp, самочувствие
5. **Не спрашивай** упражнения/веса/повторы, если GymUp-данные подтверждены

Если экспорт не удался — переходи к ручному сбору (шаг 4 в `weekly-review.md`).

## Формат вывода format-weekly.py

Markdown-блок по дням:

- дата, день недели (Пн/Вт/Чт/Пт)
- тоннаж, число сетов и упражнений
- упражнения: `вес×повторы/вес×повторы/...`
- пропущенные упражнения (есть в плане, нет подходов)
- сводная таблица за период

## Сопоставление названий упражнений

В `workout.db` у каталожных упражнений `exercise_name` пустой — имя берётся из APK:
`res_thExName{th_exercise_id}` (см. `~/gymup-sync/catalog/exercises-ru-*.json`).

`export-workouts.sh` обогащает JSON полем `exercise_name_resolved`.

Алгоритм `format-weekly.py`:

1. `exercise_name_resolved` из каталога APK
2. Иначе `exercise_name` из БД (пользовательские упражнения)
3. Иначе — сопоставление по `exercise_order` и дню недели с `docs/user/current_program.md`
4. Иначе — `упр. #N`

Каталог: `python3 ~/gymup-sync/scripts/build-exercise-catalog.py` (нужен `jadx` + `adb` при обновлении GymUp).

## Анализ для weekly review

После получения данных из GymUp:

| Метрика | Как считать |
|---------|-------------|
| Выполнение плана | тренировок факт vs 4 запланированных |
| Объём | сеты и тоннаж по дням vs прошлая неделя |
| Ключевые веса | топ-упражнения: факт vs `current_program.md` |
| Пропуски | упражнения без подходов в GymUp |
| Прогрессия | повышение веса при сохранении повторений |

Предлагай изменения рабочих весов только после подтверждения пользователя.

## Файлы

| Путь | Назначение |
|------|------------|
| `~/gymup-sync/export-workouts.sh` | Экспорт JSON/CSV/summary |
| `.cursor/skills/gymup-sync/scripts/export-workouts.py` | Каноническая копия экспортёра (восстановить в `~/gymup-sync/scripts/` при поломке) |
| `~/gymup-sync/server.py` | HTTP-триггер с телефона |
| `~/gymup-sync/output/` | Экспорты `workouts-lastNd-*.json` |
| `~/gymup-sync/catalog/` | Кэш каталога упражнений `exercises-ru-*.json` |
| `~/gymup-sync/scripts/build-exercise-catalog.py` | Сборка каталога из APK |
| `.cursor/skills/gymup-sync/scripts/format-weekly.py` | Markdown для weekly review |

## Ошибки

| Симптом | Решение |
|---------|---------|
| `no device` | USB-кабель, `adb devices`, или `ADB_WIRELESS` в config |
| `no workout.db backups` | Сделать тренировку в GymUp (автобэкап после сессии) |
| `trainings=0` | Увеличить окно: `export-workouts.sh 14` |
| Пустые названия | `build-exercise-catalog.py`; fallback — `current_program.md` |
| `jadx not found` | `brew install jadx` для пересборки каталога |

## Связанные команды

- `/weekly-review` — основной потребитель
- `/log-workout` — можно дополнять GymUp-данными RPE и заметками
- `fitness-coach` skill — координирует общий workflow
