"""Basic construction tests for dataclasses.

Dataclasses are simple by design, but these quick checks catch accidental
renames or default changes that would ripple through code using them.
"""

from domain import models


def test_iprange_model():
    ip = models.IPRange(value="203.0.113.0/24", ip_type="v4")
    assert ip.value.endswith("/24")
    assert ip.ip_type == "v4"


def test_firewallrule_model_defaults():
    ip = models.IPRange(value="2001:db8::/32", ip_type="v6")
    rule = models.FirewallRule(ip_range=ip, port=443, protocol="tcp", action="allow")
    assert rule.comment is None
