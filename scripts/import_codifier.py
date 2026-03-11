#!/usr/bin/env python3
"""
import_codifier.py — импорт структуры кодификатора ЕГЭ из JSON-файлов в базу данных.

Использование:
    # Импорт всех *.json файлов из директории content/
    python scripts/import_codifier.py

    # Импорт одного или нескольких конкретных файлов
    python scripts/import_codifier.py content/chemistry.v1.json content/biology.v1.json

    # Указать другой путь к базе данных
    DB_PATH=path/to/bot.db python scripts/import_codifier.py

Импорт идемпотентен: повторный запуск обновит существующие записи без дублирования.
"""

import json
import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path, чтобы импортировать database.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import database  # noqa: E402


SUPPORTED_VERSIONS = {1}
CONTENT_DIR = PROJECT_ROOT / "content"


def _load_file(path: Path) -> dict:
    """Загрузить и распарсить JSON-файл кодификатора."""
    with open(path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Файл {path}: невалидный JSON — {exc}") from exc
    return data


def _validate(data: dict, path: Path) -> None:
    """Проверить обязательные поля и ссылки внутри файла."""
    name = str(path)

    version = data.get("version")
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(
            f"{name}: неподдерживаемая версия формата '{version}'. "
            f"Поддерживаются: {sorted(SUPPORTED_VERSIONS)}"
        )

    for field in ("subject", "themes", "exam_tasks", "mapping"):
        if field not in data or data[field] is None:
            raise ValueError(f"{name}: отсутствует обязательное поле '{field}'")

    subject = data["subject"]
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError(f"{name}: поле 'subject' должно быть непустой строкой")

    # Проверяем темы
    theme_ids = set()
    for i, theme in enumerate(data["themes"]):
        for field in ("id", "name"):
            if field not in theme or not theme[field]:
                raise ValueError(f"{name}: themes[{i}]: отсутствует поле '{field}'")
        tid = theme["id"]
        if tid in theme_ids:
            raise ValueError(f"{name}: themes: дублирующийся id '{tid}'")
        theme_ids.add(tid)
        parent = theme.get("parent_id")
        if parent is not None and not isinstance(parent, str):
            raise ValueError(f"{name}: themes[{i}] '{tid}': parent_id должен быть строкой или null")

    # Проверяем задания
    task_ids = set()
    for i, task in enumerate(data["exam_tasks"]):
        for field in ("id", "number", "name"):
            if field not in task or not str(task.get(field, "")).strip():
                raise ValueError(f"{name}: exam_tasks[{i}]: отсутствует поле '{field}'")
        tid = task["id"]
        if tid in task_ids:
            raise ValueError(f"{name}: exam_tasks: дублирующийся id '{tid}'")
        task_ids.add(tid)

    # Проверяем маппинг
    for i, entry in enumerate(data["mapping"]):
        if not entry.get("exam_task_id"):
            raise ValueError(f"{name}: mapping[{i}]: отсутствует поле 'exam_task_id'")
        if not isinstance(entry.get("theme_ids"), list):
            raise ValueError(f"{name}: mapping[{i}]: поле 'theme_ids' должно быть списком")
        etid = entry["exam_task_id"]
        if etid not in task_ids:
            raise ValueError(
                f"{name}: mapping[{i}]: exam_task_id '{etid}' не найден в exam_tasks"
            )
        for theme_id in entry["theme_ids"]:
            if theme_id not in theme_ids:
                raise ValueError(
                    f"{name}: mapping[{i}] (exam_task_id='{etid}'): "
                    f"theme_id '{theme_id}' не найден в themes"
                )


def _import_file(data: dict, path: Path) -> dict:
    """Импортировать данные одного файла в базу. Возвращает словарь с количеством записей."""
    subject = data["subject"]
    counts = {"themes": 0, "exam_task_types": 0, "exam_task_theme_map": 0}

    for theme in data["themes"]:
        database.upsert_theme(
            subject=subject,
            theme_id=theme["id"],
            name=theme["name"],
            parent_id=theme.get("parent_id"),
        )
        counts["themes"] += 1

    for task in data["exam_tasks"]:
        database.upsert_exam_task_type(
            subject=subject,
            exam_task_id=task["id"],
            number=str(task["number"]),
            name=task["name"],
            part=task.get("part"),
        )
        counts["exam_task_types"] += 1

    for entry in data["mapping"]:
        database.set_exam_task_theme_map(
            subject=subject,
            exam_task_id=entry["exam_task_id"],
            theme_ids=entry["theme_ids"],
        )
        counts["exam_task_theme_map"] += len(entry["theme_ids"])

    return counts


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # Определяем список файлов для импорта
    if argv:
        paths = [Path(p) for p in argv]
    else:
        paths = sorted(CONTENT_DIR.glob("*.json"))
        if not paths:
            print(f"Нет JSON-файлов в директории {CONTENT_DIR}")
            return 1

    # Инициализируем БД (создаём таблицы, если их нет)
    database.init_db()

    total_counts: dict[str, int] = {}
    errors: list[str] = []
    success: list[str] = []

    for path in paths:
        path = path.resolve()
        if not path.exists():
            errors.append(f"  ❌ {path}: файл не найден")
            continue
        try:
            data = _load_file(path)
            _validate(data, path)
            counts = _import_file(data, path)
            subject = data["subject"]
            subject_name = data.get("subject_name") or subject
            success.append(
                f"  ✅ {path.name} ({subject_name}): "
                f"тем={counts['themes']}, "
                f"типов заданий={counts['exam_task_types']}, "
                f"записей маппинга={counts['exam_task_theme_map']}"
            )
            for key, val in counts.items():
                total_counts[key] = total_counts.get(key, 0) + val
        except (ValueError, KeyError, OSError) as exc:
            errors.append(f"  ❌ {path.name}: {exc}")

    print("\n=== Результаты импорта ===")
    for line in success:
        print(line)
    for line in errors:
        print(line)

    if success:
        print(
            f"\nИтого импортировано: "
            f"тем={total_counts.get('themes', 0)}, "
            f"типов заданий={total_counts.get('exam_task_types', 0)}, "
            f"записей маппинга={total_counts.get('exam_task_theme_map', 0)}"
        )

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
