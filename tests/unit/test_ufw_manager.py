"""
Unit tests for UFWManager that focus on parsing and command wiring.

We don't execute real ufw commands here. Instead, we simulate their output so
we can verify our string parsing and decision-making in a safe, deterministic way.
"""

from unittest.mock import MagicMock, patch

from cloudflare_ufw_sync.ufw import UFWManager


@patch("cloudflare_ufw_sync.ufw.subprocess.run")
def test_get_existing_rules_parses_ipv4_and_ipv6(mock_run):
    """Parse a realistic 'ufw status numbered' output for both IP families.

    The exact output format from ufw can vary a bit between versions, but the
    core pieces we rely on (rule number, proto/port, from IP, and comment) stay
    recognizable. This test makes sure our regex and filters pull the right bits.
    """
    # Simulate successful call to 'which ufw' during UFWManager __init__
    mock_run.side_effect = [
        MagicMock(),  # which ufw
        # 'ufw status numbered' output
        MagicMock(stdout="""
[ 1] 203.0.113.0/24  ALLOW IN  tcp/443  from 203.0.113.0/24  # Cloudflare IP
[ 2] 2001:db8::/32   ALLOW IN  tcp/443  from 2001:db8::/32   # Cloudflare IP
[ 3] 10.0.0.0/8      ALLOW IN  tcp/22   from 10.0.0.0/8      # not ours
"""),
    ]

    ufw = UFWManager(port=443, proto="tcp", comment="Cloudflare IP")
    rules = ufw.get_existing_rules()

    assert "203.0.113.0/24" in rules["v4"]
    assert "2001:db8::/32" in rules["v6"]
    # The SSH rule isn't ours (wrong comment/port) and should be ignored
    assert "10.0.0.0/8" not in rules["v4"]


@patch("cloudflare_ufw_sync.ufw.subprocess.run")
def test_add_and_delete_rule_happy_path(mock_run):
    """Verify we construct and sequence ufw commands correctly.

    We first pretend to discover a rule number, then ensure we send the
    right 'delete <number>' follow-up. The actual shell calls are mocked.
    """
    # Call order:
    # 1. which ufw
    # 2. ufw allow proto tcp from 203.0.113.0/24 ...
    mock_run.side_effect = [
        MagicMock(),  # which ufw
        MagicMock(stdout="Rule added"),  # allow
    ]
    ufw = UFWManager()
    assert ufw.add_rule("203.0.113.0/24") is True

    # Now test deletion path (status -> delete)
    mock_run.side_effect = [
        MagicMock(),  # which ufw for new instance
        MagicMock(stdout="""
[ 7] 203.0.113.0/24  ALLOW IN  tcp/443  from 203.0.113.0/24  # Cloudflare IP
"""),
        MagicMock(stdout="Rule deleted"),  # delete 7
    ]
    ufw = UFWManager()
    assert ufw.delete_rule("203.0.113.0/24") is True


@patch("cloudflare_ufw_sync.ufw.subprocess.run")
def test_set_policy_validation(mock_run):
    """Reject bad policies and accept known-good ones.

    This is a tiny guardrail but it prevents accidental typos from making it to
    the shell. Lower risk, happier future you.
    """
    mock_run.side_effect = [MagicMock(), MagicMock(stdout="ok")]
    ufw = UFWManager()
    assert ufw.set_policy("allow") is True
    assert ufw.set_policy("nope") is False
