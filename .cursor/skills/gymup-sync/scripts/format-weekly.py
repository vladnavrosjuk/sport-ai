#!/usr/bin/env python3
"""Format GymUp export JSON into a weekly-review markdown block."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

WEEKDAY_TO_DAY = {
    0: 1,  # Mon -> День 1
    1: 2,  # Tue -> День 2
    3: 3,  # Thu -> День 3
    4: 4,  # Fri -> День 4
}

DAY_NAMES = {1: "Пн", 2: "Вт", 3: "Чт", 4: "Пт"}
RU_WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def parse_program_exercises(program_path: Path) -> dict[int, list[str]]:
    """Extract ordered exercise names per program day (1-4)."""
    text = program_path.read_text(encoding="utf-8")
    days: dict[int, list[str]] = {1: [], 2: [], 3: [], 4: []}
    current_day = 0
    for line in text.splitlines():
        m = re.match(r"^## День (\d+)", line)
        if m:
            current_day = int(m.group(1))
            continue
        if current_day and line.startswith("|") and not line.startswith("| ---"):
            cols = [c.strip() for c in line.split("|")]
            if len(cols) >= 4 and cols[1].isdigit():
                name = cols[2].strip()
                if name and name != "#":
                    days.setdefault(current_day, []).append(name)
    return days


def find_latest_json(output_dir: Path) -> Path:
    files = sorted(output_dir.glob("workouts-last*d-*.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"no export JSON in {output_dir}")
    return files[-1]


def load_rows(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("expected JSON array")
    return data


def fmt_weight(w: float | None) -> str:
    if w is None:
        return "—"
    if w == int(w):
        return str(int(w))
    return str(w).rstrip("0").rstrip(".")


def fmt_sets(sets: list[tuple[float | None, float | None]]) -> str:
    parts = []
    for w, r in sets:
        if w is None and r is None:
            continue
        parts.append(f"{fmt_weight(w)}×{fmt_weight(r)}")
    return "/".join(parts) if parts else "пропущено"


def pick_exercise_name(row: dict) -> str:
    resolved = (row.get("exercise_name_resolved") or "").strip()
    if resolved:
        return resolved
    return (row.get("exercise_name") or "").strip()


def resolve_name(
    exercise_name: str,
    order: int,
    program_day: int,
    program_exercises: dict[int, list[str]],
) -> str:
    name = (exercise_name or "").strip()
    if name:
        return name
    exercises = program_exercises.get(program_day, [])
    idx = order - 1
    if 0 <= idx < len(exercises):
        return exercises[idx]
    return f"упр. #{order}"


def build_report(
    rows: list[dict],
    program_exercises: dict[int, list[str]],
    days_window: int,
) -> str:
    trainings: dict[int, dict] = {}
    workouts: dict[tuple[int, int], dict] = defaultdict(lambda: {"sets": [], "meta": {}})

    for row in rows:
        tid = row["training_id"]
        if tid not in trainings:
            started = row["started_at"]
            dt = datetime.strptime(started, "%Y-%m-%d %H:%M:%S")
            trainings[tid] = {
                "started_at": started,
                "finished_at": row.get("finished_at"),
                "weekday": RU_WEEKDAYS[dt.weekday()],
                "program_day": WEEKDAY_TO_DAY.get(dt.weekday(), 0),
                "exercises_count": row.get("exercises_count"),
                "sets_count": row.get("sets_count"),
                "tonnage_kg": row.get("tonnage_kg"),
            }
        wid = row["workout_id"]
        key = (tid, wid)
        workouts[key]["meta"] = {
            "order": row.get("exercise_order") or 0,
            "name": pick_exercise_name(row),
            "rule": row.get("planned_rule"),
        }
        if row.get("weight_kg") is not None or row.get("reps") is not None:
            workouts[key]["sets"].append((row.get("weight_kg"), row.get("reps")))

    lines = [
        f"# GymUp — тренировки за последние {days_window} дней",
        "",
        f"**Тренировок:** {len(trainings)}",
        "",
    ]

    total_tonnage = 0.0
    total_sets = 0

    for tid in sorted(trainings, key=lambda x: trainings[x]["started_at"]):
        t = trainings[tid]
        date_short = t["started_at"][:10]
        day_label = DAY_NAMES.get(t["program_day"], t["weekday"])
        tonnage = t.get("tonnage_kg") or 0
        sets = t.get("sets_count") or 0
        total_tonnage += tonnage
        total_sets += sets

        lines.append(f"## {date_short} ({day_label})")
        lines.append(
            f"**{tonnage / 1000:.2f} т** · {sets} сетов · {t.get('exercises_count', '?')} упр."
        )
        lines.append("")

        session_workouts = [
            (k, v) for k, v in workouts.items() if k[0] == tid and v["sets"]
        ]
        session_workouts.sort(key=lambda x: x[1]["meta"]["order"])

        for (_, _), wdata in session_workouts:
            meta = wdata["meta"]
            name = resolve_name(
                meta["name"],
                meta["order"],
                t["program_day"],
                program_exercises,
            )
            result = fmt_sets(wdata["sets"])
            lines.append(f"- **{name}** — {result}")

        skipped = [
            (k, v)
            for k, v in workouts.items()
            if k[0] == tid and not v["sets"] and v["meta"].get("rule")
        ]
        if skipped:
            lines.append("")
            lines.append("*Пропущены (без подходов):*")
            for (_, _), wdata in sorted(skipped, key=lambda x: x[1]["meta"]["order"]):
                meta = wdata["meta"]
                name = resolve_name(
                    meta["name"],
                    meta["order"],
                    t["program_day"],
                    program_exercises,
                )
                lines.append(f"- {name} ({meta.get('rule', '')})")

        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## Сводка",
            "",
            f"| Метрика | Значение |",
            f"|---------|----------|",
            f"| Тренировок | {len(trainings)} |",
            f"| Всего сетов | {total_sets} |",
            f"| Суммарный тоннаж | {total_tonnage / 1000:.2f} т |",
            f"| Средний тоннаж/тренировка | {total_tonnage / max(len(trainings), 1) / 1000:.2f} т |",
            "",
            "> Источник: GymUp (ADB). Названия из каталога APK (`res_thExName{id}`), иначе — `current_program.md` по порядку и дню недели.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Format GymUp JSON for weekly review")
    parser.add_argument("json", nargs="?", help="Path to export JSON (default: latest in output dir)")
    parser.add_argument(
        "--program",
        default="docs/user/current_program.md",
        help="Path to current program for exercise name resolution",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path.home() / "gymup-sync" / "output"),
        help="GymUp sync output directory",
    )
    parser.add_argument("--days", type=int, default=7, help="Days window (for report header)")
    parser.add_argument("-o", "--out", help="Write markdown to file")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[4]
    program_path = Path(args.program)
    if not program_path.is_absolute():
        program_path = repo_root / program_path

    if args.json:
        json_path = Path(args.json)
    else:
        json_path = find_latest_json(Path(args.output_dir))

    program_exercises = parse_program_exercises(program_path) if program_path.is_file() else {}
    rows = load_rows(json_path)
    report = build_report(rows, program_exercises, args.days)

    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(args.out)
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
