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
        MagicMock(
            stdout="""
[ 1] 203.0.113.0/24  ALLOW IN  tcp/443  from 203.0.113.0/24  # Cloudflare IP
[ 2] 2001:db8::/32   ALLOW IN  tcp/443  from 2001:db8::/32   # Cloudflare IP
[ 3] 10.0.0.0/8      ALLOW IN  tcp/22   from 10.0.0.0/8      # not ours
"""
        ),
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
        MagicMock(
            stdout="""
[ 7] 203.0.113.0/24  ALLOW IN  tcp/443  from 203.0.113.0/24  # Cloudflare IP
"""
        ),
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


@patch("cloudflare_ufw_sync.ufw.subprocess.run")
def test_ensure_enabled_active_short_circuits(mock_run):
    """When UFW is already active, we don't try to enable it again."""
    # which ufw, then status verbose returns active
    mock_run.side_effect = [
        MagicMock(),
        MagicMock(stdout="Status: active"),
    ]
    ufw = UFWManager()
    assert ufw.ensure_enabled() is True


@patch("cloudflare_ufw_sync.ufw.subprocess.run")
def test_ensure_enabled_enables_when_inactive(mock_run):
    """If UFW is inactive, we call '--force enable' and return its result."""
    # which ufw, status verbose inactive, then enable ok
    mock_run.side_effect = [
        MagicMock(),
        MagicMock(stdout="Status: inactive"),
        MagicMock(stdout="enabled"),
    ]
    ufw = UFWManager()
    assert ufw.ensure_enabled() is True


@patch("cloudflare_ufw_sync.ufw.subprocess.run")
def test_get_existing_rules_ignores_malformed_lines(mock_run):
    """A weird line shouldn't crash parsing; we just skip it politely."""
    mock_run.side_effect = [
        MagicMock(),
        MagicMock(stdout="""
[ 1] nonsense without expected tokens
[ 2] 2001:db8::/32   ALLOW IN  tcp/443  from 2001:db8::/32   # Cloudflare IP
"""),
    ]
    ufw = UFWManager()
    rules = ufw.get_existing_rules()
    assert "2001:db8::/32" in rules["v6"]


@patch("cloudflare_ufw_sync.ufw.subprocess.run")
def test_get_existing_rules_ignores_other_ports(mock_run):
    """Rules that match the comment but different port/proto should be ignored."""
    mock_run.side_effect = [
        MagicMock(),
        MagicMock(stdout="""
[ 1] 203.0.113.0/24  ALLOW IN  tcp/80  from 203.0.113.0/24  # Cloudflare IP
[ 2] 2001:db8::/32   ALLOW IN  tcp/443 from 2001:db8::/32   # Cloudflare IP
"""),
    ]
    ufw = UFWManager(port=443, proto="tcp", comment="Cloudflare IP")
    rules = ufw.get_existing_rules()
    # tcp/80 should be ignored; tcp/443 kept
    assert "203.0.113.0/24" not in rules["v4"]
    assert "2001:db8::/32" in rules["v6"]


@patch("cloudflare_ufw_sync.ufw.subprocess.run")
def test_delete_rule_not_found_returns_false(mock_run):
    """If we can't find a rule number, we fail gracefully and return False."""
    mock_run.side_effect = [
        MagicMock(),
        MagicMock(stdout="""
[ 1] some other thing # Cloudflare IP
"""),
    ]
    ufw = UFWManager()
    assert ufw.delete_rule("***********/24") is False


@patch("cloudflare_ufw_sync.ufw.subprocess.run")
def test_get_existing_rules_status_failure(mock_run, monkeypatch):
    """If 'ufw status' fails, we return empty sets and don't crash."""
    # which ufw succeeds, then our _run_ufw_command returns failure
    mock_run.return_value = MagicMock()
    m = UFWManager
    # Patch the instance method to simulate a failure tuple
    monkeypatch.setattr(m, "_run_ufw_command", lambda self, args: (False, "boom"))
    ufw = UFWManager()
    rules = ufw.get_existing_rules()
    assert rules == {"v4": set(), "v6": set()}


@patch("cloudflare_ufw_sync.ufw.subprocess.run")
def test_add_rule_failure(mock_run, monkeypatch):
    """If adding a rule fails, we report False (and log)."""
    # which ufw ok
    mock_run.return_value = MagicMock()
    ufw = UFWManager()
    monkeypatch.setattr(ufw, "_run_ufw_command", lambda args: (False, "nope"))
    assert ufw.add_rule("***********/24") is False


@patch("cloudflare_ufw_sync.ufw.subprocess.run")
def test_delete_rule_status_failure(mock_run, monkeypatch):
    """If the numbered status fails, delete_rule returns False right away."""
    # which ufw ok
    mock_run.return_value = MagicMock()
    ufw = UFWManager()
    # First call is status numbered -> fail
    calls = iter([(False, "err")])
    monkeypatch.setattr(ufw, "_run_ufw_command", lambda args: next(calls))
    assert ufw.delete_rule("***********/24") is False


@patch("cloudflare_ufw_sync.ufw.subprocess.run")
def test_set_policy_command_failure(mock_run, monkeypatch):
    """Even with a valid policy, a command failure should return False."""
    # which ufw ok
    mock_run.return_value = MagicMock()
    ufw = UFWManager()
    monkeypatch.setattr(ufw, "_run_ufw_command", lambda args: (False, "err"))
    assert ufw.set_policy("deny") is False


@patch("cloudflare_ufw_sync.ufw.subprocess.run")
def test_ensure_enabled_enable_failure(mock_run, monkeypatch):
    """Inactive -> enable fails -> returns False."""
    # which ufw ok
    mock_run.return_value = MagicMock()
    ufw = UFWManager()
    seq = iter([
        (True, "Status: inactive"),  # status verbose
        (False, "enable failed"),    # --force enable
    ])
    monkeypatch.setattr(ufw, "_run_ufw_command", lambda args: next(seq))
    assert ufw.ensure_enabled() is False
