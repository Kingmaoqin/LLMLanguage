"""Canonical Stage-2.5b social-style rendering utilities."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def stable_text_hash(text: str | None) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def load_style_templates(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(
        payload.get("conditions"), dict
    ):
        raise ValueError(f"invalid social-style template file: {path}")
    return payload


def template_by_id(
    spec: dict[str, Any],
    condition: str,
    template_id: str,
) -> dict[str, Any]:
    try:
        templates = spec["conditions"][condition]["templates"]
    except KeyError as exc:
        raise KeyError(f"unknown social-style condition: {condition!r}") from exc
    for template in templates:
        if template["template_id"] == template_id:
            return template
    raise KeyError(
        f"template_id={template_id!r} not found for condition={condition!r}"
    )


def template_ids(spec: dict[str, Any], condition: str) -> list[str]:
    try:
        return [
            str(template["template_id"])
            for template in spec["conditions"][condition]["templates"]
        ]
    except KeyError as exc:
        raise KeyError(f"unknown social-style condition: {condition!r}") from exc


@dataclass(frozen=True)
class StyleTemplate:
    condition: str
    mode: str
    template_id: str
    text: str


@dataclass
class SocialStyleWrapper:
    template: StyleTemplate
    user_turn_idx: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)

    def should_wrap(self, clean_text: str, *, is_stop: bool) -> bool:
        if is_stop or not clean_text or not self.template.text:
            return False
        if self.template.mode == "first_turn_only":
            return self.user_turn_idx == 0
        if self.template.mode == "every_user_turn":
            return True
        raise ValueError(f"unknown social-style mode: {self.template.mode}")

    def render(
        self,
        clean_text: str,
        *,
        is_stop: bool,
    ) -> tuple[str, dict[str, Any]]:
        wrapped = self.should_wrap(clean_text, is_stop=is_stop)
        styled_text = (
            f"{self.template.text} {clean_text}" if wrapped else clean_text
        )
        event = {
            "condition": self.template.condition,
            "style_template_id": self.template.template_id,
            "user_turn_idx": self.user_turn_idx,
            "mode": self.template.mode,
            "wrapped": wrapped,
            "wrapper_text": self.template.text if wrapped else "",
            "clean_content_hash": stable_text_hash(clean_text),
            "styled_content_hash": stable_text_hash(styled_text),
            "clean_word_count": len(clean_text.split()),
            "wrapper_word_count": (
                len(self.template.text.split()) if wrapped else 0
            ),
        }
        self.events.append(event)
        self.user_turn_idx += 1
        return styled_text, event


def style_template(
    condition: str,
    *,
    template_id: str | None = None,
    template_text: str | None = None,
) -> StyleTemplate:
    mode = (
        "every_user_turn"
        if condition.endswith("_repeated")
        else "first_turn_only"
    )
    return StyleTemplate(
        condition=condition,
        mode=mode,
        template_id=template_id or f"{condition}_0",
        text=template_text or "",
    )
