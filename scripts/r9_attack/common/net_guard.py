#!/usr/bin/env python3
"""R9 outbound-network kill switch (spec 0.2, 3.2, 18).

Spec 0.2 requires `outbound network disabled` to be *verified*, not asserted, and spec
18 requires `outbound network event = 0` in the integrity accounting. Both benchmarks
run third-party code (BFCL executable backends, ToolSandbox tools, model handlers) that
would happily reach the public internet if a scenario or a dependency tried to, so the
guard is installed process-wide before any adapter is imported.

Policy: only loopback and explicitly allowlisted cluster-internal hosts may be dialled.
Everything else raises `OutboundNetworkBlocked` AND is appended to an in-process event
log which `check_integrity.py` folds into the run accounting.
"""
from __future__ import annotations

import ipaddress
import socket
from typing import Any, Iterable

# Events recorded here are surfaced by `drain_events()`; a non-empty list fails spec 18.
_EVENTS: list[dict[str, Any]] = []
_INSTALLED = False
_ALLOWED_HOSTS: set[str] = set()

_ORIG_CONNECT = socket.socket.connect
_ORIG_CONNECT_EX = socket.socket.connect_ex
_ORIG_CREATE_CONNECTION = socket.create_connection


class OutboundNetworkBlocked(RuntimeError):
    """Raised when sandboxed code attempts to reach a non-local address."""


def _is_local(host: str) -> bool:
    """True for loopback literals, `localhost`, and explicitly allowlisted hosts."""
    if host in _ALLOWED_HOSTS:
        return True
    if host in ("localhost", "localhost.localdomain", ""):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        # A name that is not allowlisted would need DNS -> treat as outbound.
        return False
    return bool(ip.is_loopback)


def _check(address: Any, api: str) -> None:
    # AF_UNIX sockets pass a str path; those never leave the machine.
    if not isinstance(address, tuple) or not address:
        return
    host = str(address[0])
    if _is_local(host):
        return
    event = {"api": api, "host": host, "port": address[1] if len(address) > 1 else None}
    _EVENTS.append(event)
    raise OutboundNetworkBlocked(
        f"R9 sandbox blocked outbound {api} to {host}:{event['port']}; "
        "only loopback and allowlisted cluster hosts are reachable (spec 0.2)."
    )


def install(allowed_hosts: Iterable[str] = ()) -> None:
    """Patch socket dialling. Idempotent; extra `allowed_hosts` accumulate.

    `allowed_hosts` are the cluster-internal model endpoints from the model manifest.
    They must still be non-public: `safety_audit.py` re-checks that separately.
    """
    global _INSTALLED
    _ALLOWED_HOSTS.update(str(h) for h in allowed_hosts)
    if _INSTALLED:
        return

    def guarded_connect(self, address):  # type: ignore[no-untyped-def]
        _check(address, "connect")
        return _ORIG_CONNECT(self, address)

    def guarded_connect_ex(self, address):  # type: ignore[no-untyped-def]
        _check(address, "connect_ex")
        return _ORIG_CONNECT_EX(self, address)

    def guarded_create_connection(address, *args, **kwargs):  # type: ignore[no-untyped-def]
        _check(address, "create_connection")
        return _ORIG_CREATE_CONNECTION(address, *args, **kwargs)

    socket.socket.connect = guarded_connect  # type: ignore[method-assign]
    socket.socket.connect_ex = guarded_connect_ex  # type: ignore[method-assign]
    socket.create_connection = guarded_create_connection  # type: ignore[assignment]
    _INSTALLED = True


def uninstall() -> None:
    """Restore the stdlib socket API. Only used by tests."""
    global _INSTALLED
    socket.socket.connect = _ORIG_CONNECT  # type: ignore[method-assign]
    socket.socket.connect_ex = _ORIG_CONNECT_EX  # type: ignore[method-assign]
    socket.create_connection = _ORIG_CREATE_CONNECTION  # type: ignore[assignment]
    _INSTALLED = False
    _ALLOWED_HOSTS.clear()


def is_installed() -> bool:
    return _INSTALLED


def events() -> list[dict[str, Any]]:
    return list(_EVENTS)


def drain_events() -> list[dict[str, Any]]:
    out = list(_EVENTS)
    _EVENTS.clear()
    return out


def selftest() -> dict[str, Any]:
    """Active probe used by `safety_audit.py`: prove the guard actually blocks.

    Dials a public address (TEST-NET-1, 192.0.2.1, RFC 5737 — never routable) and a
    loopback address, and reports both outcomes. Does not depend on real connectivity.
    """
    blocked = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        try:
            s.connect(("192.0.2.1", 80))
        finally:
            s.close()
    except OutboundNetworkBlocked:
        blocked = True
    except OSError:
        # Guard not installed and the address is simply unreachable -> NOT proof.
        blocked = False
    # The probe intentionally pollutes the event log; remove it so the run accounting
    # only counts genuine attempts made by benchmark/attacker code.
    _EVENTS[:] = [e for e in _EVENTS if e.get("host") != "192.0.2.1"]

    local_ok = True
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        try:
            s.connect_ex(("127.0.0.1", 1))  # refused is fine; blocked is not
        finally:
            s.close()
    except OutboundNetworkBlocked:
        local_ok = False
    except OSError:
        local_ok = True

    return {
        "guard_installed": _INSTALLED,
        "outbound_blocked": blocked,
        "loopback_allowed": local_ok,
        "allowed_hosts": sorted(_ALLOWED_HOSTS),
    }
