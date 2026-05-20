#!/usr/bin/env python3
"""Consistency checks for Sport AI Workplace."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMAND_RE = re.compile(r"`(/[-a-z0-9]+)`")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def collect_declared_commands() -> dict[str, set[str]]:
    files = [
        ROOT / "AGENTS.md",
        ROOT / "README.md",
        ROOT / ".cursor/rules/workflow.mdc",
        ROOT / ".cursor/skills/fitness-coach/SKILL.md",
        ROOT / "agents/fitness-coach/AGENT.md",
    ]
    result: dict[str, set[str]] = {}
    for path in files:
        commands = set(COMMAND_RE.findall(read_text(path)))
        if commands:
            result[str(path.relative_to(ROOT))] = commands
    manifest_path = ROOT / "agents/fitness-coach/manifest.json"
    if manifest_path.exists():
        manifest = json.loads(read_text(manifest_path))
        commands = {
            item["name"]
            for item in manifest.get("commands", {}).get("implemented", [])
            if "name" in item
        }
        declared_only = set(manifest.get("commands", {}).get("declaredOnly", []))
        result[str(manifest_path.relative_to(ROOT))] = commands | declared_only
    return result


def check_command_files(warnings: list[str], errors: list[str]) -> None:
    for source, commands in collect_declared_commands().items():
        for command in sorted(commands):
            filename = command.strip("/").replace("/", "-") + ".md"
            path = ROOT / ".cursor/commands" / filename
            if not path.exists():
                errors.append(f"{source}: command {command} has no {path.relative_to(ROOT)}")


def check_manifest(warnings: list[str], errors: list[str]) -> None:
    manifest_path = ROOT / "agents/fitness-coach/manifest.json"
    if not manifest_path.exists():
        errors.append("agents/fitness-coach/manifest.json is missing")
        return
    try:
        manifest = json.loads(read_text(manifest_path))
    except json.JSONDecodeError as exc:
        errors.append(f"manifest.json is invalid JSON: {exc}")
        return

    for key in ["skill", "instructions"]:
        value = manifest.get(key)
        if isinstance(value, str) and not (ROOT / value).exists():
            errors.append(f"manifest {key} points to missing file: {value}")
        if isinstance(value, list):
            for item in value:
                if not (ROOT / item).exists():
                    errors.append(f"manifest {key} points to missing file: {item}")

    for item in manifest.get("commands", {}).get("implemented", []):
        file_path = item.get("file")
        if file_path and not (ROOT / file_path).exists():
            errors.append(f"manifest command {item.get('name')} points to missing file: {file_path}")


def check_json_data(warnings: list[str], errors: list[str]) -> None:
    data_dir = ROOT / "docs/user/data"
    required = [
        "profile.json",
        "weights.json",
        "nutrition.json",
        "strength_records.json",
        "workouts.json",
        "metrics.json",
    ]
    for name in required:
        path = data_dir / name
        if not path.exists():
            errors.append(f"missing structured data file: {path.relative_to(ROOT)}")
            continue
        try:
            json.loads(read_text(path))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.relative_to(ROOT)} is invalid JSON: {exc}")


def check_dashboard(warnings: list[str], errors: list[str]) -> None:
    dashboard = ROOT / "docs/user/dashboard.html"
    text = read_text(dashboard)
    if not text:
        errors.append("docs/user/dashboard.html is missing or empty")
        return
    if "Обновлено:" not in text:
        errors.append("dashboard has no update marker")
    if "Сегодня в зале" not in text:
        warnings.append("dashboard has no gym quick-start block")
    if "Риски недели" not in text:
        warnings.append("dashboard has no weekly risks block")


def check_fitness_metrics(warnings: list[str], errors: list[str]) -> None:
    required = [
        ROOT / "docs/user/measurements_log.md",
        ROOT / "docs/user/recovery_log.md",
    ]
    for path in required:
        if not path.exists():
            errors.append(f"missing fitness metrics file: {path.relative_to(ROOT)}")


def check_review_dirs(warnings: list[str], errors: list[str]) -> None:
    for folder in ["docs/user/weekly_reviews", "docs/user/monthly_reviews"]:
        path = ROOT / folder
        if not path.exists():
            errors.append(f"missing review directory: {folder}")
        elif not any(path.iterdir()):
            warnings.append(f"review directory is empty: {folder}")


def main() -> int:
    warnings: list[str] = []
    errors: list[str] = []

    check_command_files(warnings, errors)
    check_manifest(warnings, errors)
    check_json_data(warnings, errors)
    check_dashboard(warnings, errors)
    check_fitness_metrics(warnings, errors)
    check_review_dirs(warnings, errors)

    if errors:
        status = "FIX REQUIRED"
    elif warnings:
        status = "WARN"
    else:
        status = "OK"

    print(f"Sport AI health-check: {status}")
    for item in errors:
        print(f"ERROR: {item}")
    for item in warnings:
        print(f"WARN: {item}")
    return 2 if errors else 1 if warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
