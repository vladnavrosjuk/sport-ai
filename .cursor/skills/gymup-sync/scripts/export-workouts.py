#!/usr/bin/env python3
"""Export GymUp workouts from workout.db to JSON/CSV for weekly review."""
from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

BACKUP_GLOB = "/sdcard/Android/data/com.adaptech.gymup/files/backups/*_workout.db"


def log(msg: str) -> None:
    print(f"[gymup-export] {msg}", flush=True)


def load_config(root: Path) -> dict[str, str]:
    cfg: dict[str, str] = {}
    config_path = root / "config"
    if not config_path.is_file():
        return cfg
    for line in config_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            cfg[key.strip()] = val.strip().strip('"').strip("'")
    return cfg


def adb_device_ready(wireless: str | None) -> bool:
    try:
        subprocess.run(["adb", "get-state"], check=True, capture_output=True, text=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        if wireless:
            subprocess.run(["adb", "connect", wireless], capture_output=True, text=True)
            try:
                subprocess.run(["adb", "get-state"], check=True, capture_output=True, text=True)
                return True
            except subprocess.CalledProcessError:
                return False
        return False


def latest_backup_remote() -> str | None:
    result = subprocess.run(
        ["adb", "shell", f"ls -t {BACKUP_GLOB} 2>/dev/null | head -1"],
        capture_output=True,
        text=True,
    )
    line = (result.stdout or "").strip()
    return line if line.endswith("_workout.db") else None


def pull_latest_db(dest: Path, wireless: str | None) -> Path:
    if not adb_device_ready(wireless):
        raise RuntimeError("adb: no device (connect USB or set ADB_WIRELESS in config)")
    remote = latest_backup_remote()
    if not remote:
        raise RuntimeError("no workout.db backups on device; finish a workout in GymUp")
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["adb", "pull", remote, str(dest)], check=True, capture_output=True, text=True)
    log(f"pulled {remote}")
    return dest


def resolve_db(root: Path, cfg: dict[str, str]) -> Path:
    env_db = os.environ.get("GYMUP_DB")
    if env_db:
        path = Path(env_db)
        if not path.is_file():
            raise FileNotFoundError(f"GYMUP_DB not found: {path}")
        return path
    if cfg.get("GYMUP_DB"):
        path = Path(cfg["GYMUP_DB"]).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"GYMUP_DB in config not found: {path}")
        return path
    cache = root / ".cache" / "workout.db"
    return pull_latest_db(cache, cfg.get("ADB_WIRELESS"))


def ms_to_str(ms: int | None) -> str | None:
    if not ms:
        return None
    value = float(ms)
    if value > 1e12:
        value /= 1000.0
    return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def export_rows(db_path: Path, days: int) -> list[dict]:
    since = datetime.now() - timedelta(days=days)
    since_ms = int(since.timestamp() * 1000)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows: list[dict] = []
    cur.execute(
        """
        SELECT t._id AS training_id,
               t.startDateTime,
               t.finishDateTime,
               t.name AS training_name,
               t.comment AS training_comment,
               t.exercisesAmount,
               t.setsAmount,
               t.repsAmount,
               t.tonnage,
               t.time AS duration_raw,
               t.calories,
               w._id AS workout_id,
               w.order_num AS exercise_order,
               w.th_exercise_id,
               w.rule AS planned_rule,
               w.comment AS exercise_comment,
               s._id AS set_id,
               s.weight AS weight_kg,
               s.reps,
               s.time AS set_time_sec,
               s.distance AS distance_m,
               s.hard_sense AS rpe,
               s.comment AS set_comment,
               s.finishDateTime AS set_finish_ms
        FROM training t
        JOIN workout w ON w.training_id = t._id
        LEFT JOIN set_ s ON s.workout_id = w._id
        WHERE t.startDateTime >= ?
        ORDER BY t.startDateTime, w.order_num, s._id
        """,
        (since_ms,),
    )

    emitted_empty: set[int] = set()
    for r in cur:
        base = {
            "training_id": r["training_id"],
            "started_at": ms_to_str(r["startDateTime"]),
            "finished_at": ms_to_str(r["finishDateTime"]),
            "training_name": r["training_name"],
            "training_comment": r["training_comment"],
            "exercises_count": r["exercisesAmount"],
            "sets_count": r["setsAmount"],
            "reps_total": r["repsAmount"],
            "tonnage_kg": r["tonnage"],
            "duration_sec": r["duration_raw"],
            "calories": r["calories"],
            "workout_id": r["workout_id"],
            "exercise_order": r["exercise_order"],
            "th_exercise_id": r["th_exercise_id"],
            "exercise_added_by_user": 0,
            "exercise_name": "",
            "planned_rule": r["planned_rule"],
            "exercise_comment": r["exercise_comment"],
            "set_id": r["set_id"],
            "weight_kg": r["weight_kg"],
            "reps": r["reps"],
            "set_time_sec": r["set_time_sec"],
            "distance_m": r["distance_m"],
            "rpe": r["rpe"],
            "set_comment": r["set_comment"],
            "set_finished_at": ms_to_str(r["set_finish_ms"]),
        }
        if r["set_id"] is not None:
            rows.append(base)
        elif r["workout_id"] not in emitted_empty:
            emitted_empty.add(r["workout_id"])
            rows.append(base)

    conn.close()
    return rows


def training_ids(rows: list[dict]) -> set[int]:
    return {int(r["training_id"]) for r in rows if r.get("training_id") is not None}


def write_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "started_at",
        "exercise_name",
        "th_exercise_id",
        "weight_kg",
        "reps",
        "set_time_sec",
        "set_comment",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            if row.get("set_id") is None:
                continue
            writer.writerow(
                {
                    "started_at": row.get("started_at", ""),
                    "exercise_name": row.get("exercise_name_resolved")
                    or row.get("exercise_name")
                    or "",
                    "th_exercise_id": row.get("th_exercise_id", ""),
                    "weight_kg": row.get("weight_kg", ""),
                    "reps": row.get("reps", ""),
                    "set_time_sec": row.get("set_time_sec", ""),
                    "set_comment": row.get("set_comment", ""),
                }
            )


def write_summary(path: Path, rows: list[dict]) -> None:
    by_training: dict[int, dict] = {}
    for row in rows:
        tid = row["training_id"]
        if tid not in by_training:
            by_training[tid] = {
                "started_at": row["started_at"],
                "exercises": row.get("exercises_count") or 0,
                "sets": row.get("sets_count") or 0,
                "tonnage_kg": row.get("tonnage_kg") or 0,
            }
    lines = [
        "    started_at       exercises  sets  tonnage_kg",
        "-------------------  ---------  ----  ----------",
    ]
    for meta in sorted(by_training.values(), key=lambda m: m["started_at"], reverse=True):
        started = meta["started_at"].replace(" ", " ", 1)[:19]
        lines.append(
            f"{started:>19}  {meta['exercises']:>9}  {meta['sets']:>4}  {meta['tonnage_kg']:>10}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def enrich(json_path: Path, root: Path, csv_path: Path | None) -> None:
    enrich_script = root / "scripts" / "enrich-workouts.py"
    if not enrich_script.is_file():
        log("enrich-workouts.py missing; skipping catalog enrichment")
        return
    cmd = [sys.executable, str(enrich_script), str(json_path)]
    if csv_path:
        cmd.extend(["--csv", str(csv_path)])
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export GymUp workouts")
    parser.add_argument("days", nargs="?", type=int, default=7, help="Days window (default: 7)")
    parser.add_argument("--root", type=Path, help="gymup-sync root (default: parent of scripts/)")
    args = parser.parse_args()

    root = args.root or Path(__file__).resolve().parent.parent
    cfg = load_config(root)
    days = max(1, args.days)

    try:
        db_path = resolve_db(root, cfg)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1

    rows = export_rows(db_path, days)
    trainings = len(training_ids(rows))

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = root / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"workouts-last{days}d-{stamp}"
    json_path = out_dir / f"{prefix}.json"
    csv_path = out_dir / f"{prefix}.csv"
    summary_path = out_dir / f"{prefix}-summary.txt"

    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        enrich(json_path, root, csv_path)
    except subprocess.CalledProcessError as exc:
        log(f"enrich failed: {exc}")
    write_csv(csv_path, json.loads(json_path.read_text(encoding="utf-8")))
    write_summary(summary_path, rows)

    log(f"trainings={trainings} sets={sum(1 for r in rows if r.get('set_id'))} -> {json_path.name}")
    result = {
        "ok": True,
        "trainings": trainings,
        "days": days,
        "db": str(db_path),
        "json": str(json_path),
        "csv": str(csv_path),
        "summary": str(summary_path),
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
