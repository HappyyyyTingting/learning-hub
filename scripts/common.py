#!/usr/bin/env python3
"""Shared helpers for Learning Hub.

A task lives in its own top-level directory: ``daily-<task>/``.
Everything task-specific (config, prompt, schema, fixture, content, state,
renderer) lives there; this module only knows how to find it.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DEFAULT_TASK = "english"
TASK_DIR_PREFIX = "daily-"


def normalize_task(task: str | None = None) -> str:
    value = (task or os.getenv("TASK") or DEFAULT_TASK).strip().lower()
    if value.startswith(TASK_DIR_PREFIX):
        value = value[len(TASK_DIR_PREFIX) :]
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", value):
        raise ValueError(f"任务名只能包含小写字母、数字和连字符：{value}")
    return value


def task_dir(task: str | None = None) -> Path:
    return ROOT / f"{TASK_DIR_PREFIX}{normalize_task(task)}"


def list_tasks() -> list[str]:
    return sorted(
        path.parent.name[len(TASK_DIR_PREFIX) :]
        for path in ROOT.glob(f"{TASK_DIR_PREFIX}*/config.yml")
    )


def _resolve(base: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else base / path


def load_config(task: str | None = None) -> dict:
    task_id = normalize_task(task)
    path = task_dir(task_id) / "config.yml"
    with path.open(encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    if not isinstance(config, dict):
        raise ValueError(f"配置文件格式不正确：{path}")
    config["id"] = task_id
    return config


def resolve_date(value: str | None, config: dict) -> str:
    if value:
        if not DATE_RE.match(value):
            raise ValueError(f"日期格式应为 YYYY-MM-DD：{value}")
        datetime.strptime(value, "%Y-%m-%d")
        return value
    tz = ZoneInfo(config.get("timezone", "Asia/Shanghai"))
    return datetime.now(tz).date().isoformat()


def content_dir(task: str | None = None, config: dict | None = None) -> Path:
    task_id = normalize_task(task)
    config = config or load_config(task_id)
    return _resolve(task_dir(task_id), str(config.get("content_dir", "content")))


def content_path(
    task: str | None,
    date_text: str,
    config: dict | None = None,
) -> Path:
    return content_dir(task, config) / f"{date_text}.json"


def state_path(task: str | None = None, config: dict | None = None) -> Path:
    task_id = normalize_task(task)
    config = config or load_config(task_id)
    return _resolve(task_dir(task_id), str(config.get("state", "state/sent.json")))


def schema_path(task: str | None = None, config: dict | None = None) -> Path:
    task_id = normalize_task(task)
    config = config or load_config(task_id)
    return _resolve(task_dir(task_id), str(config.get("schema", "schema.json")))


def prompt_path(task: str | None = None, config: dict | None = None) -> Path:
    task_id = normalize_task(task)
    config = config or load_config(task_id)
    return _resolve(task_dir(task_id), str(config.get("prompt", "prompts/v2.md")))


def fixture_path(task: str | None = None) -> Path:
    return task_dir(task) / "fixture.json"


def site_dir(task: str | None = None, config: dict | None = None) -> Path:
    task_id = normalize_task(task)
    config = config or load_config(task_id)
    return _resolve(ROOT, str(config.get("site_dir", f"site/{task_id}")))


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


def load_content(
    task: str | None,
    date_text: str,
    config: dict | None = None,
) -> dict:
    return load_json(content_path(task, date_text, config))


def list_content_dates(task: str | None = None, config: dict | None = None) -> list[str]:
    directory = content_dir(task, config)
    if not directory.is_dir():
        return []
    dates = [p.stem for p in directory.glob("*.json") if DATE_RE.match(p.stem)]
    return sorted(dates)


def load_all_contents(task: str | None = None, config: dict | None = None) -> list[dict]:
    results = []
    for date_text in list_content_dates(task, config):
        try:
            results.append(load_content(task, date_text, config))
        except (OSError, ValueError):
            continue
    return results


def load_schema(task: str | None = None, config: dict | None = None) -> dict:
    return load_json(schema_path(task, config))


def load_fixture(task: str | None = None) -> dict:
    return load_json(fixture_path(task))


def load_prompt(task: str | None = None, config: dict | None = None) -> str:
    return prompt_path(task, config).read_text(encoding="utf-8")


def load_renderer(task: str | None = None):
    """Import ``daily-<task>/render.py`` as a standalone module."""
    task_id = normalize_task(task)
    path = task_dir(task_id) / "render.py"
    if not path.is_file():
        raise ValueError(f"任务缺少 render.py：{path}")

    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    module_name = f"learning_hub_task_{task_id.replace('-', '_')}_render"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"无法加载任务渲染器：{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


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


def derive_site_url(task: str | None = None) -> str:
    explicit = os.getenv("SITE_URL", "").strip()
    if explicit:
        base = explicit
    else:
        repository = os.getenv("GITHUB_REPOSITORY", "").strip()
        if not repository or "/" not in repository:
            return ""
        owner, name = repository.split("/", 1)
        base = f"https://{owner.lower()}.github.io/{name}/"
    if task:
        return base.rstrip("/") + f"/{normalize_task(task)}/"
    return base


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_sent_state(task: str | None = None, config: dict | None = None) -> dict:
    path = state_path(task, config)
    if not path.is_file():
        return {"sent": {}}
    try:
        data = load_json(path)
    except (OSError, ValueError):
        return {"sent": {}}
    sent = data.get("sent")
    return {"sent": sent if isinstance(sent, dict) else {}}


def is_sent(
    task: str | None,
    date_text: str,
    config: dict | None = None,
) -> bool:
    return date_text in load_sent_state(task, config)["sent"]


def mark_sent(
    task: str | None,
    date_text: str,
    config: dict | None = None,
) -> None:
    state = load_sent_state(task, config)
    state["sent"][date_text] = now_utc()
    write_json(state_path(task, config), state)
