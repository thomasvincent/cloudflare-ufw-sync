"""
CLI tests

We aim for lightweight checks here: argument parsing and ensuring the handlers
wire up without actually forking daemons or touching systemd. Anything that
would poke the real system is mocked.
"""

from unittest.mock import MagicMock, patch

from cloudflare_ufw_sync.cli import (
    handle_install,
    handle_status,
    handle_sync,
    handle_uninstall,
    main,
    parse_args,
)
from cloudflare_ufw_sync.config import Config


def test_parse_args_basics():
    """The top-level flags and subcommands should parse cleanly."""
    ns = parse_args(["--verbose", "sync", "--force"])
    assert ns.verbose is True
    assert ns.command == "sync"
    assert ns.force is True


def test_main_no_command_returns_1():
    """Calling main([]) should print usage guidance and return 1."""
    assert main([]) == 1


@patch("cloudflare_ufw_sync.cli.SyncService")
def test_handle_sync_success(mock_sync_service_cls):
    """A successful sync returns exit code 0 and prints a friendly summary."""
    mock_service = MagicMock()
    mock_service.sync.return_value = {
        "ips": {"v4": 1, "v6": 2},
        "rules": {"added": 3, "removed": 0},
    }
    mock_sync_service_cls.return_value = mock_service

    rc = handle_sync(Config(), force=False)
    assert rc == 0
    mock_service.sync.assert_called_once()


@patch("cloudflare_ufw_sync.ufw.UFWManager")
def test_handle_status_counts_rules(mock_ufw_cls):
    """Status should show counts of v4 and v6 rules.

    We don't assert on stdout text here (that's brittle), just that we asked
    for rules and returned a success code.
    """
    mock_ufw = MagicMock()
    mock_ufw.get_existing_rules.return_value = {"v4": {"x"}, "v6": set()}
    mock_ufw_cls.return_value = mock_ufw

    rc = handle_status(Config())
    assert rc == 0
    mock_ufw.get_existing_rules.assert_called_once()


@patch("cloudflare_ufw_sync.cli.Path.exists", return_value=False)
def test_handle_install_missing_service_file(mock_exists):
    """If the service file isn't present, we should bail with a clear error."""
    rc = handle_install(Config(), no_enable=True)
    assert rc == 1


@patch("subprocess.run")
@patch("shutil.copy")
@patch("cloudflare_ufw_sync.cli.Path.exists", return_value=True)
@patch("cloudflare_ufw_sync.cli.Path")
def test_handle_install_success(mock_path_cls, mock_exists, mock_copy, mock_run):
    """Happy path: service file exists, we copy it, reload daemon, and do not enable when --no-enable is set.

    Everything that would touch the real system is mocked: filesystem and systemctl calls.
    """
    # Make Path(...)/"scripts"/"cloudflare-ufw-sync.service" behave like it exists
    mock_service_path = MagicMock()
    mock_joined = MagicMock()
    mock_joined.exists.return_value = True
    # simulate /etc/systemd/system destination path for printing
    mock_path_cls.return_value.__truediv__.return_value = mock_joined

    rc = handle_install(Config(), no_enable=True)

    assert rc == 0
    mock_copy.assert_called()  # service file copied
    # We should at least have reloaded the daemon
    mock_run.assert_any_call(["systemctl", "daemon-reload"], check=True)


@patch("subprocess.run")
@patch("cloudflare_ufw_sync.cli.Path")
def test_handle_uninstall_success(mock_path_cls, mock_run):
    """Uninstall should stop/disable service, remove file if present, and reload daemon.

    We patch Path(...).exists() to True and Path(...).unlink() to succeed.
    """
    mock_service_file = MagicMock()
    mock_service_file.exists.return_value = True
    mock_path_cls.return_value = mock_service_file

    rc = handle_uninstall(Config())

    assert rc == 0
    # stop/disable may be non-checking; we just ensure daemon reload is called
    mock_run.assert_any_call(["systemctl", "daemon-reload"], check=True)
    assert mock_service_file.unlink.called


@patch("cloudflare_ufw_sync.cli.SyncService")
@patch("cloudflare_ufw_sync.cli.os.fork", return_value=1234)
def test_handle_daemon_parent_returns_immediately(mock_fork, mock_sync_cls):
    """When not in foreground, parent process should return 0 and not run daemon."""
    rc = __import__("cloudflare_ufw_sync.cli", fromlist=["handle_daemon"]).handle_daemon(
        Config(), foreground=False
    )
    assert rc == 0
    mock_sync_cls.assert_not_called()


@patch("cloudflare_ufw_sync.cli.SyncService")
def test_handle_daemon_foreground_calls_run(mock_sync_cls):
    """Foreground mode should call SyncService.run_daemon and return 0."""
    mock_service = MagicMock()
    mock_sync_cls.return_value = mock_service
    rc = __import__("cloudflare_ufw_sync.cli", fromlist=["handle_daemon"]).handle_daemon(
        Config(), foreground=True
    )
    assert rc == 0
    mock_service.run_daemon.assert_called_once()


@patch("cloudflare_ufw_sync.cli.SyncService")
def test_handle_sync_error_path(mock_sync_cls):
    """If sync() raises, handler should return 1 and log an error (no exception)."""
    mock_service = MagicMock()
    mock_service.sync.side_effect = RuntimeError("boom")
    mock_sync_cls.return_value = mock_service
    rc = handle_sync(Config(), force=False)
    assert rc == 1


@patch("subprocess.run")
@patch("shutil.copy")
@patch("cloudflare_ufw_sync.cli.Path.exists", return_value=True)
@patch("cloudflare_ufw_sync.cli.Path")
def test_handle_install_enables_when_no_flag(mock_path_cls, mock_exists, mock_copy, mock_run):
    """Install without --no-enable should enable and start service (calls mocked)."""
    mock_joined = MagicMock()
    mock_joined.exists.return_value = True
    mock_path_cls.return_value.__truediv__.return_value = mock_joined

    rc = handle_install(Config(), no_enable=False)

    assert rc == 0
    mock_run.assert_any_call(["systemctl", "daemon-reload"], check=True)
    mock_run.assert_any_call(["systemctl", "enable", "cloudflare-ufw-sync"], check=True)
    mock_run.assert_any_call(["systemctl", "start", "cloudflare-ufw-sync"], check=True)
