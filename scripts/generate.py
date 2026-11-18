#!/usr/bin/env python3
"""Generate one day's task content with the DeepSeek API.

Examples:
    python scripts/generate.py --task english --fixture --date 2026-11-09
    python scripts/generate.py --task english --date 2026-11-09
    python scripts/generate.py --task english --date 2026-11-09 --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date as date_cls
from datetime import datetime

import common


def _to_date(value: str) -> date_cls:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _previous_contents(contents: list[dict], date_text: str) -> list[dict]:
    return sorted(
        (
            content
            for content in contents
            if common.DATE_RE.match(str(content.get("date", "")))
            and str(content.get("date", "")) < date_text
        ),
        key=lambda content: str(content.get("date", "")),
    )


def detect_mode(contents: list[dict], date_text: str) -> str:
    """讲解日和复习日交替；漏跑一天也不会打乱顺序。"""
    previous = _previous_contents(contents, date_text)
    if not previous:
        return "lesson"
    return "review" if common.content_mode(previous[-1]) == "lesson" else "lesson"


def build_review_targets(contents: list[dict], date_text: str) -> dict | None:
    """复习日只复习最近一次讲解日的 5 个词。"""
    for content in reversed(_previous_contents(contents, date_text)):
        if common.content_mode(content) != "lesson":
            continue
        words = [word for word in (content.get("words") or []) if word.get("term")]
        if not words:
            continue
        targets = []
        for word in words:
            targets.append(
                {
                    "term": str(word.get("term", "")).strip(),
                    "first_seen": str(content.get("date", "")),
                    "exam_focus_zh": str(word.get("exam_focus_zh", "")).strip(),
                    "senses": [
                        {
                            "pos": str(sense.get("pos", "")).strip(),
                            "definition_zh": str(sense.get("definition_zh", "")).strip(),
                            "definition_en": str(sense.get("definition_en", "")).strip(),
                        }
                        for sense in (word.get("senses") or [])
                    ],
                    "synonyms": [
                        {
                            "term": str(item.get("term", "")).strip(),
                            "nuance_zh": str(item.get("nuance_zh", "")).strip(),
                        }
                        for item in (word.get("synonyms") or [])
                    ],
                    "collocations": [
                        str(item.get("phrase", "")).strip()
                        for item in (word.get("collocations") or [])
                    ],
                    "examples": [
                        str(item.get("sentence", "")).strip()
                        for item in (word.get("examples") or [])
                    ],
                }
            )
        return {
            "review_of": str(content.get("date", "")),
            "theme": str(content.get("theme", "")).strip(),
            "title": str(content.get("title", "")).strip(),
            "words": targets,
        }
    return None


def review_target_errors(content: dict, targets: dict | None) -> list[str]:
    """复习日只能复习上一讲的 5 个词，防止模型自行换词。"""
    expected = [
        str(item.get("term", "")).strip()
        for item in ((targets or {}).get("words") or [])
    ]
    actual = [
        str(item.get("term", "")).strip()
        for item in (content.get("review_words") or [])
    ]
    if sorted(expected) != sorted(actual):
        return [
            "review_words 必须正好是上一讲的 5 个词："
            + "、".join(expected)
        ]
    return []


def build_review_candidates(contents: list[dict], today: date_cls) -> list[dict]:
    """Pick words first seen 3/7/14 days ago and not reviewed recently."""
    history: dict[str, dict] = {}
    for content in contents:
        date_text = str(content.get("date", ""))
        try:
            seen = _to_date(date_text)
        except ValueError:
            continue
        if seen >= today:
            continue
        for word in content.get("words", []):
            term = str(word.get("term", "")).strip()
            if not term:
                continue
            item = history.setdefault(
                term,
                {"term": term, "first_seen": date_text, "last_reviewed": ""},
            )
            if date_text < item["first_seen"]:
                item["first_seen"] = date_text
        reviews = list(content.get("review") or []) + list(
            content.get("review_words") or []
        )
        for review in reviews:
            term = str(review.get("term", "")).strip()
            if term in history and date_text > history[term]["last_reviewed"]:
                history[term]["last_reviewed"] = date_text

    candidates = []
    for item in history.values():
        try:
            first_seen = _to_date(item["first_seen"])
        except ValueError:
            continue
        days_since_first = (today - first_seen).days
        if days_since_first not in (3, 7, 14):
            continue
        if item["last_reviewed"]:
            try:
                days_since_review = (today - _to_date(item["last_reviewed"])).days
            except ValueError:
                days_since_review = 999
            if days_since_review < 3:
                continue
        candidates.append(
            {
                "term": item["term"],
                "first_seen": item["first_seen"],
                "days_since_first_seen": days_since_first,
            }
        )
    candidates.sort(key=lambda item: (item["days_since_first_seen"], item["term"]))
    return candidates[:10]


def build_context(
    task: str,
    date_text: str,
    config: dict,
    contents: list[dict],
    today: date_cls,
    mode: str = "lesson",
    review_targets: dict | None = None,
) -> dict:
    recent = [content for content in contents if content.get("date", "") < date_text]
    recent_themes: list[str] = []
    recent_words: list[str] = []
    for content in sorted(recent, key=lambda item: item.get("date", ""), reverse=True)[:14]:
        theme = str(content.get("theme", "")).strip()
        if theme and theme not in recent_themes:
            recent_themes.append(theme)
        for word in content.get("words", []):
            term = str(word.get("term", "")).strip()
            if term and term not in recent_words:
                recent_words.append(term)
    context = {
        "date": date_text,
        "task": task,
        "level": config.get("level", ""),
        "prompt_version": config.get("prompt_version", ""),
        "mode": common.normalize_mode(mode),
        "recent_themes": recent_themes[:7],
        "recent_words": recent_words[:60],
        "review_candidates": build_review_candidates(recent, today),
    }
    if context["mode"] == "review":
        context["review_of"] = (review_targets or {}).get("review_of", "")
        context["theme"] = (review_targets or {}).get("theme", "")
        context["review_targets"] = (review_targets or {}).get("words", [])
        # 复习日只围绕上一讲的 5 个词，不需要新词和间隔复习上下文。
        for key in ("recent_themes", "recent_words", "review_candidates"):
            context.pop(key, None)
    return context


def _parse_json_object(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        raise ValueError("模型返回空内容（DeepSeek JSON 模式下通常是模型没有输出合法 JSON）")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("模型返回的不是 JSON 对象")
    return data


def call_model(
    system_prompt: str,
    context: dict,
    config: dict,
    schema: dict,
    model: str | None,
    extra_validator=None,
) -> dict:
    import openai

    provider = str(config.get("provider", "deepseek")).strip().lower()
    if provider != "deepseek":
        raise RuntimeError(f"当前只支持 provider=deepseek，收到：{provider}")

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("缺少 DEEPSEEK_API_KEY 环境变量")

    client = openai.OpenAI(
        api_key=api_key,
        base_url=str(config.get("base_url", "https://api.deepseek.com")),
    )
    model_name = model or str(config.get("model", "deepseek-flash"))
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": "今天的生成上下文：\n\n"
            + json.dumps(context, ensure_ascii=False, indent=2)
            + "\n\n输出必须符合以下 JSON Schema：\n"
            + json.dumps(schema, ensure_ascii=False)
            + "\n\n请只输出一个 JSON 对象，不要加代码块或解释。",
        },
    ]

    attempts = 3
    for attempt in range(1, attempts + 1):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=int(config.get("max_tokens", 8000)),
                temperature=float(config.get("temperature", 1.0)),
            )
        except Exception as exc:  # noqa: BLE001 - 把 SDK 异常转成可读错误
            raise RuntimeError(f"DeepSeek 请求失败：{exc}") from exc

        choice = response.choices[0]
        if choice.finish_reason == "length":
            raise RuntimeError("模型输出被 max_tokens 截断，请调大 config.yml 的 max_tokens")

        text = choice.message.content or ""
        try:
            content = _parse_json_object(text)
        except ValueError as exc:
            if attempt >= attempts:
                raise RuntimeError(f"模型没有返回有效 JSON：{exc}") from exc
            messages.append({"role": "assistant", "content": text or "{}"})
            messages.append(
                {
                    "role": "user",
                    "content": f"上面的输出不是有效 JSON：{exc}。请只输出一个完整的 JSON 对象，不要加代码块或解释。",
                }
            )
            continue

        errors = common.validate_content(content, schema)
        if not errors and extra_validator is not None:
            errors = extra_validator(content)
        if not errors:
            return content
        if attempt >= attempts:
            raise RuntimeError("模型输出不符合 schema：" + "; ".join(errors[:5]))
        messages.append({"role": "assistant", "content": text})
        messages.append(
            {
                "role": "user",
                "content": "上面的 JSON 不符合 schema，请修正后重新输出完整 JSON。错误：\n"
                + "\n".join(errors[:10]),
            }
        )

    raise RuntimeError("模型调用失败：重试次数已用尽")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成一天的任务推送内容。")
    parser.add_argument("--task", default="", help="任务名，例如 english（默认）")
    parser.add_argument("--date", help="日期 YYYY-MM-DD；默认按 config 时区取今天")
    parser.add_argument("--fixture", action="store_true", help="使用 fixture，不调用 API")
    parser.add_argument("--force", action="store_true", help="覆盖已存在的内容")
    parser.add_argument("--dry-run", action="store_true", help="只打印 prompt 和上下文")
    parser.add_argument("--model", help="覆盖 config 中的模型")
    parser.add_argument(
        "--mode",
        choices=("auto", "lesson", "review"),
        default="auto",
        help="auto 按上一篇自动切换；lesson 讲解日；review 复习日",
    )
    args = parser.parse_args(argv)

    try:
        task = common.normalize_task(args.task)
        config = common.load_config(task)
        date_text = common.resolve_date(args.date, config)
        target = common.content_path(task, date_text, config)
        if target.is_file() and not args.force and not args.dry_run:
            print(f"内容已存在，跳过生成：{target}")
            return 0

        contents = common.load_all_contents(task, config)
        mode = (
            detect_mode(contents, date_text)
            if args.mode == "auto"
            else common.normalize_mode(args.mode)
        )
        review_targets = (
            build_review_targets(contents, date_text) if mode == "review" else None
        )
        if mode == "review" and not review_targets:
            raise ValueError(
                "今天是复习日，但没有找到上一节讲解内容；"
                "请先用 --mode lesson 生成讲解日，或改用 --mode lesson。"
            )

        if args.fixture:
            content = common.load_fixture(task, mode)
            content["date"] = date_text
            content["task"] = task
            content["level"] = config.get("level", "")
            content["prompt_version"] = config.get("prompt_version", "")
            content["mode"] = mode
            # fixture 是自洽的样例，不覆盖 review_of/theme；真实生成才使用上面的 targets。
            schema = common.load_schema(task, config, mode)
            errors = common.validate_content(content, schema)
            if errors:
                print(f"fixture 不符合 schema（mode={mode}）：", file=sys.stderr)
                for error in errors:
                    print(f"  - {error}", file=sys.stderr)
                return 1
            if args.dry_run:
                print(f"dry-run：fixture 校验通过（mode={mode}），将写入 {target}")
                return 0
            common.write_json(target, content)
            print(f"已写入 fixture 内容（mode={mode}）：{target}")
            return 0

        system_prompt = common.load_prompt(task, config, mode)
        today = _to_date(date_text)
        context = build_context(
            task,
            date_text,
            config,
            contents,
            today,
            mode=mode,
            review_targets=review_targets,
        )

        if args.dry_run:
            print(f"=== mode: {mode} ===")
            print("=== system prompt ===")
            print(system_prompt)
            print("\n=== context ===")
            print(json.dumps(context, ensure_ascii=False, indent=2))
            return 0

        schema = common.load_schema(task, config, mode)
        extra_validator = (
            (lambda candidate: review_target_errors(candidate, review_targets))
            if mode == "review"
            else None
        )
        content = call_model(
            system_prompt,
            context,
            config,
            schema,
            args.model,
            extra_validator,
        )

        # 权威字段由脚本覆盖，避免模型写错日期、模式或版本。
        content["date"] = date_text
        content["task"] = task
        content["level"] = config.get("level", "")
        content["prompt_version"] = config.get("prompt_version", "")
        content["mode"] = mode
        if mode == "review":
            content["review_of"] = review_targets["review_of"]
            content["theme"] = review_targets["theme"]

        errors = common.validate_content(content, schema)
        if errors:
            print("生成内容不符合 schema：", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 1

        if mode == "lesson":
            recent_terms = set(context["recent_words"])
            duplicates = [
                word.get("term")
                for word in content.get("words", [])
                if word.get("term") in recent_terms
            ]
            if duplicates:
                print(f"提示：今天有词在最近 14 天出现过：{', '.join(duplicates)}")

        common.write_json(target, content)
        print(f"已生成：{target}")
        print(f"模式：{mode}｜主题：{content.get('theme')}｜标题：{content.get('title')}")
        if mode == "review":
            print(
                f"复习：{len(content.get('review_words', []))} 个词"
                f"｜练习：{len(content.get('quiz', []))}"
            )
        else:
            print(
                f"词汇：{len(content.get('words', []))}"
                f"｜复习：{len(content.get('review', []))}"
            )
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
