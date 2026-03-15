# Команда: /fitness-init

Полная инициализация фитнес-профиля пользователя.

## Описание

Эта команда запускает пошаговый опрос для создания персонализированного профиля.
По завершении создаётся файл `.cursor/project/user_profile.md` со всеми данными.

## Фазы инициализации

### Фаза 1: Базовые данные
- Имя, возраст, пол
- Рост и вес

### Фаза 2: Тренировочный опыт
- Стаж тренировок
- Текущие силовые показатели (1RM)
- Травмы и ограничения

### Фаза 3: Цели
- Основная цель (набор/сила/похудение)
- Целевые показатели
- Временные рамки

### Фаза 4: Образ жизни
- Доступные дни для тренировок
- Оборудование
- Сон и стресс
- Пищевые предпочтения

### Фаза 5: Генерация профиля
- Расчёт BMR, TDEE, макросов
- Определение уровня подготовки
- Создание файла профиля

## Результат

После завершения:
1. Создан файл `.cursor/project/user_profile.md`
2. Рассчитаны все показатели
3. Предложены следующие команды:
   - `/generate-workout` — создать программу тренировок
   - `/generate-nutrition` — создать план питания
   - `/generate-full` — создать всё вместе

## Связанные правила

- [user_data_collection.mdc](mdc:../rules/initialization/user_data_collection.mdc)
- [basic_data.mdc](mdc:../rules/initialization/basic_data.mdc)
- [training_experience.mdc](mdc:../rules/initialization/training_experience.mdc)
- [goals_collection.mdc](mdc:../rules/initialization/goals_collection.mdc)
- [lifestyle.mdc](mdc:../rules/initialization/lifestyle.mdc)
- [profile_generation.mdc](mdc:../rules/initialization/profile_generation.mdc)

## Примечания

- Инициализация занимает 5-10 минут
- Можно прервать и продолжить позже
- Если профиль уже существует, будет предложено обновить или создать новый
