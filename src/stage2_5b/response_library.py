"""Deterministic rendering for the frozen scripted-user response library."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LIBRARY_PATH = (
    ROOT / "data" / "stage2_5b" / "user_response_library.yaml"
)


@dataclass(frozen=True)
class ResponseSelection:
    response_id: str
    speech_act: str
    clean_text: str


class ResponseLibrary:
    def __init__(self, payload: dict[str, Any]):
        speech_acts = payload.get("speech_acts")
        if not isinstance(speech_acts, dict) or not speech_acts:
            raise ValueError("response library requires speech_acts")
        self.speech_acts = speech_acts
        self._validate()

    @classmethod
    def load(
        cls,
        path: Path = DEFAULT_LIBRARY_PATH,
    ) -> "ResponseLibrary":
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"invalid response library: {path}")
        return cls(payload)

    def _validate(self) -> None:
        seen: set[str] = set()
        for speech_act, item in self.speech_acts.items():
            templates = item.get("templates") if isinstance(item, dict) else None
            if not isinstance(templates, list) or not templates:
                raise ValueError(
                    f"speech act {speech_act!r} requires templates"
                )
            for template in templates:
                response_id = str(template.get("id") or "")
                text = template.get("text")
                if not response_id or not isinstance(text, str) or not text:
                    raise ValueError(
                        f"invalid response template under {speech_act!r}"
                    )
                if response_id in seen:
                    raise ValueError(
                        f"duplicate response template id: {response_id}"
                    )
                seen.add(response_id)

    def render(
        self,
        *,
        task_id: str,
        seed: int,
        speech_act: str,
        state_id: str,
        slots: dict[str, Any],
    ) -> ResponseSelection:
        if speech_act not in self.speech_acts:
            raise KeyError(f"unknown speech act: {speech_act!r}")
        templates = self.speech_acts[speech_act]["templates"]
        digest = hashlib.sha256(
            f"{task_id}|{seed}|{speech_act}|{state_id}".encode("utf-8")
        ).digest()
        index = int.from_bytes(digest[:8], "big") % len(templates)
        template = templates[index]
        try:
            clean_text = str(template["text"]).format_map(slots)
        except KeyError as exc:
            raise ValueError(
                f"missing slot {exc.args[0]!r} for speech act {speech_act!r}"
            ) from exc
        return ResponseSelection(
            response_id=str(template["id"]),
            speech_act=speech_act,
            clean_text=clean_text,
        )


DEFAULT_RESPONSE_LIBRARY = ResponseLibrary.load()
