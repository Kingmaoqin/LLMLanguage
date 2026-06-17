"""Condition-specific social-style wrappers for natural tau2 user turns.

Unlike the legacy Stage-2 valence overlay, this module never creates extra
user messages and never schedules treatment based on agent tool-call counts.
It wraps only user turns that tau2 already emits.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def stable_text_hash(text: str | None) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def load_style_templates(path: Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def template_by_id(spec: dict[str, Any], condition: str, template_id: str) -> dict[str, Any]:
    for tmpl in spec["conditions"][condition]["templates"]:
        if tmpl["template_id"] == template_id:
            return tmpl
    raise KeyError(f"template_id={template_id!r} not found for condition={condition!r}")


def template_ids(spec: dict[str, Any], condition: str) -> list[str]:
    return [t["template_id"] for t in spec["conditions"][condition]["templates"]]


@dataclass
class SocialStyleController:
    condition: str
    condition_spec: dict[str, Any]
    template: dict[str, Any]
    template_block: int
    user_turn_idx: int = 0
    wrapper_events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def mode(self) -> str:
        return self.condition_spec["mode"]

    @property
    def wrapper_text(self) -> str:
        return self.template["text"]

    @property
    def template_id(self) -> str:
        return self.template["template_id"]

    def should_wrap(self, clean_content: str | None, is_stop: bool) -> bool:
        if is_stop or not clean_content:
            return False
        if self.mode == "first_turn_only":
            return self.user_turn_idx == 0
        if self.mode == "every_user_turn":
            return True
        raise ValueError(f"unknown social-style mode: {self.mode}")

    def wrap(self, clean_content: str | None, *, is_stop: bool) -> str | None:
        clean = clean_content or ""
        do_wrap = self.should_wrap(clean_content, is_stop)
        styled = f"{self.wrapper_text} {clean}" if do_wrap else clean_content
        self.wrapper_events.append({
            "condition": self.condition,
            "template_id": self.template_id,
            "template_block": self.template_block,
            "user_turn_idx": self.user_turn_idx,
            "mode": self.mode,
            "wrapped": do_wrap,
            "wrapper_text": self.wrapper_text if do_wrap else "",
            "clean_content_hash": stable_text_hash(clean_content),
            "styled_content_hash": stable_text_hash(styled),
            "clean_word_count": len(clean.split()),
            "wrapper_word_count": len(self.wrapper_text.split()) if do_wrap else 0,
        })
        self.user_turn_idx += 1
        return styled


def apply_social_style(orchestrator: Any, controller: SocialStyleController) -> None:
    """Wrap natural user turns while leaving the user simulator's internal state clean."""
    user = orchestrator.user
    if getattr(orchestrator, "solo_mode", False) or type(user).__name__ == "DummyUser":
        raise ValueError("Stage-2.5 social style requires an interactive user simulator.")

    orig_generate = user.generate_next_message
    is_stop = type(user).is_stop

    def generate_next_message(message, state):
        user_message, state = orig_generate(message, state)
        stop = is_stop(user_message)
        styled = controller.wrap(user_message.content, is_stop=stop)
        if styled != user_message.content:
            user_message = user_message.model_copy(update={"content": styled})
        return user_message, state

    user.generate_next_message = generate_next_message

