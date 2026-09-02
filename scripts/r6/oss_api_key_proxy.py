"""Small authenticated proxy for the local gpt-oss vLLM OpenAI API.

The upstream vLLM server is assumed to be running locally at 127.0.0.1:8192.
This proxy exposes the same /v1/* paths but requires:

    Authorization: Bearer $OSS_PROXY_API_KEY

It is intentionally minimal: no model logic, no prompt logging, and no request
body persistence. It exists to avoid handing out the raw unauthenticated vLLM
port to other users.
"""

from __future__ import annotations

import os
from typing import Any

import requests
from fastapi import FastAPI, Header, HTTPException, Request, Response


UPSTREAM = os.environ.get("OSS_PROXY_UPSTREAM", "http://127.0.0.1:8192").rstrip("/")
API_KEY = os.environ.get("OSS_PROXY_API_KEY", "")
TIMEOUT_SECONDS = float(os.environ.get("OSS_PROXY_TIMEOUT_SECONDS", "300"))

if not API_KEY:
    raise RuntimeError("OSS_PROXY_API_KEY must be set")

app = FastAPI(title="gpt-oss authenticated proxy", version="1.0")


def check_auth(authorization: str | None) -> None:
    expected = f"Bearer {API_KEY}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="missing or invalid bearer token")


def filtered_headers(headers: dict[str, str]) -> dict[str, str]:
    skip = {
        "host",
        "content-length",
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
    return {k: v for k, v in headers.items() if k.lower() not in skip}


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "upstream": UPSTREAM}


@app.api_route("/v1/{path:path}", methods=["GET", "POST"])
async def proxy_v1(path: str, request: Request, authorization: str | None = Header(default=None)) -> Response:
    check_auth(authorization)
    body = await request.body()
    upstream_url = f"{UPSTREAM}/v1/{path}"
    try:
        upstream_response = requests.request(
            method=request.method,
            url=upstream_url,
            params=dict(request.query_params),
            data=body if body else None,
            headers=filtered_headers(dict(request.headers)),
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"upstream request failed: {exc}") from exc

    response_headers = filtered_headers(dict(upstream_response.headers))
    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        media_type=upstream_response.headers.get("content-type"),
        headers=response_headers,
    )
