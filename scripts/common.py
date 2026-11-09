#!/usr/bin/env python3
"""Shared helpers for Learning Hub."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "tasks" / "english" / "config.yml"
STATE_PATH = ROOT / "state" / "sent.json"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    if not isinstance(config, dict):
        raise ValueError(f"配置文件格式不正确：{CONFIG_PATH}")
    return config


def resolve_date(value: str | None, config: dict) -> str:
    if value:
        if not DATE_RE.match(value):
            raise ValueError(f"日期格式应为 YYYY-MM-DD：{value}")
        datetime.strptime(value, "%Y-%m-%d")
        return value
    tz = ZoneInfo(config.get("timezone", "Asia/Shanghai"))
    return datetime.now(tz).date().isoformat()


def content_dir(config: dict | None = None) -> Path:
    config = config or load_config()
    return ROOT / config.get("content_dir", "content/english")


def content_path(date_text: str, config: dict | None = None) -> Path:
    return content_dir(config) / f"{date_text}.json"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"文件内容不是 JSON 对象：{path}")
    return data


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_content(date_text: str, config: dict | None = None) -> dict:
    return load_json(content_path(date_text, config))


def list_content_dates(config: dict | None = None) -> list[str]:
    directory = content_dir(config)
    if not directory.is_dir():
        return []
    dates = [p.stem for p in directory.glob("*.json") if DATE_RE.match(p.stem)]
    return sorted(dates)


def load_all_contents(config: dict | None = None) -> list[dict]:
    results = []
    for date_text in list_content_dates(config):
        try:
            results.append(load_content(date_text, config))
        except (OSError, ValueError):
            continue
    return results


def load_schema(config: dict | None = None) -> dict:
    config = config or load_config()
    return load_json(ROOT / config.get("schema", "tasks/english/schema.json"))


def api_schema(schema: dict) -> dict:
    """Keep only keywords the API's structured-output schema needs."""
    unsupported = {
        "$schema",
        "title",
        "description",
        "pattern",
        "format",
        "minLength",
        "maxLength",
        "minItems",
        "maxItems",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
    }

    def clean(node):
        if isinstance(node, dict):
            return {key: clean(value) for key, value in node.items() if key not in unsupported}
        if isinstance(node, list):
            return [clean(item) for item in node]
        return node

    return clean(schema)


def validate_content(content: dict, schema: dict | None = None) -> list[str]:
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(schema or load_schema())
    errors = sorted(validator.iter_errors(content), key=lambda error: list(error.path))
    return [
        f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
        for error in errors
    ]


def derive_site_url() -> str:
    explicit = os.getenv("SITE_URL", "").strip()
    if explicit:
        return explicit
    repository = os.getenv("GITHUB_REPOSITORY", "").strip()
    if repository and "/" in repository:
        owner, name = repository.split("/", 1)
        return f"https://{owner.lower()}.github.io/{name}/"
    return ""


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_sent_state() -> dict:
    if not STATE_PATH.is_file():
        return {"sent": {}}
    try:
        data = load_json(STATE_PATH)
    except (OSError, ValueError):
        return {"sent": {}}
    sent = data.get("sent")
    return {"sent": sent if isinstance(sent, dict) else {}}


def is_sent(date_text: str) -> bool:
    return date_text in load_sent_state()["sent"]


def mark_sent(date_text: str) -> None:
    state = load_sent_state()
    state["sent"][date_text] = now_utc()
    write_json(STATE_PATH, state)
