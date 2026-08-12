"""spec 0.2 / 18: outbound network must be disabled and verifiably blocked.

The net guard must block a connection to a public address while allowing loopback, must
record the blocked attempt as an event (folded into spec 18 accounting), and the safety
audit's active probe must report outbound_blocked=True.
"""
import socket

import pytest

from scripts.r9_attack.common import net_guard


@pytest.fixture(autouse=True)
def _fresh_guard():
    net_guard.uninstall()
    net_guard.drain_events()
    yield
    net_guard.uninstall()
    net_guard.drain_events()


def test_guard_blocks_public_address():
    net_guard.install(["127.0.0.1"])
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.2)
    with pytest.raises(net_guard.OutboundNetworkBlocked):
        try:
            s.connect(("192.0.2.1", 80))  # RFC5737 TEST-NET-1, never routable
        finally:
            s.close()


def test_guard_records_event():
    net_guard.install(["127.0.0.1"])
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.2)
    try:
        with pytest.raises(net_guard.OutboundNetworkBlocked):
            s.connect(("8.8.8.8", 53))
    finally:
        s.close()
    events = net_guard.events()
    assert any(e["host"] == "8.8.8.8" for e in events)


def test_guard_allows_loopback():
    net_guard.install(["127.0.0.1"])
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.2)
    try:
        # Connection may be refused (nothing listening) but must NOT be blocked by the guard.
        s.connect_ex(("127.0.0.1", 1))
    except net_guard.OutboundNetworkBlocked:
        pytest.fail("loopback wrongly blocked")
    finally:
        s.close()


def test_selftest_reports_blocked():
    net_guard.install(["127.0.0.1"])
    probe = net_guard.selftest()
    assert probe["guard_installed"] is True
    assert probe["outbound_blocked"] is True
    assert probe["loopback_allowed"] is True
