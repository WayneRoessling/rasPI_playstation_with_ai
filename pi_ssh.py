"""Shared SSH helpers for Mini-AI Pi automation scripts.

Loads connection settings from .env, provides retry-aware connect/run/gate
functions used by all phase scripts and utilities.
"""

import os
import sys
import time
import getpass
import io
import paramiko

# Fix Windows console encoding for Unicode box-drawing chars
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Config loading ────────────────────────────────────────────────────────────

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV_FILE = os.path.join(_SCRIPT_DIR, ".env")


def _load_env():
    """Read key=value pairs from .env (ignores comments and blank lines)."""
    env = {}
    if not os.path.exists(_ENV_FILE):
        return env
    with open(_ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def get_config():
    """Return (host, user, key_path) from .env with fallback to env vars."""
    env = _load_env()
    host = os.environ.get("MINI_AI_HOST") or env.get("MINI_AI_HOST")
    user = os.environ.get("MINI_AI_USER") or env.get("MINI_AI_USER")
    key = os.environ.get("MINI_AI_SSH_KEY") or env.get("MINI_AI_SSH_KEY")

    if not host or not user or not key:
        print("ERROR: Missing config. Create .env from .env.example:")
        print("  cp .env.example .env")
        sys.exit(1)

    key = os.path.expanduser(key)
    return host, user, key


def get_password():
    """Return Pi password from .env or interactive prompt (for key push only)."""
    env = _load_env()
    pw = os.environ.get("MINI_AI_PASS") or env.get("MINI_AI_PASS")
    if not pw:
        pw = getpass.getpass("Pi password (for initial key push): ")
    return pw


# ── SSH connection with retry ─────────────────────────────────────────────────

def connect(host=None, user=None, key_path=None, retries=3, delay=10):
    """Connect to Pi via SSH key with retry logic.

    Returns a paramiko.SSHClient. Raises SystemExit after exhausting retries.
    """
    if host is None:
        host, user, key_path = get_config()

    for attempt in range(1, retries + 1):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            key = paramiko.Ed25519Key.from_private_key_file(key_path)
            client.connect(host, username=user, pkey=key, timeout=15)
            return client
        except Exception as e:
            if attempt == retries:
                print(f"*** SSH connect failed after {retries} attempts: {e} ***")
                sys.exit(1)
            print(f"  Connect attempt {attempt}/{retries} failed: {e} — retry in {delay}s...")
            time.sleep(delay)


def connect_password(host, user, password):
    """Connect to Pi via password auth (for initial key push only).

    Tries standard password auth, then keyboard-interactive fallback.
    Returns (SSHClient, Transport).
    """
    t = paramiko.Transport((host, 22))
    t.connect()
    try:
        t.auth_password(user, password)
    except paramiko.AuthenticationException:
        t.auth_interactive_dumb(user, lambda title, instr, prompts: [password] * len(prompts))
    c = paramiko.SSHClient()
    c._transport = t
    return c, t


# ── Command execution ─────────────────────────────────────────────────────────

def run(client, cmd, timeout=120, label=None, abort_on_fail=True):
    """Run a command over SSH, stream output, return (exit_code, stdout_text).

    Aborts the script on non-zero exit when abort_on_fail is True.
    """
    tag = label or cmd[:70]
    print(f"\n{'─' * 60}")
    print(f"  {tag}")
    print(f"{'─' * 60}")
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    stdout.channel.set_combine_stderr(False)
    out = ""
    for line in iter(stdout.readline, ""):
        print(f"  {line}", end="")
        out += line
    err = stderr.read().decode().strip()
    if err:
        print(f"  [stderr] {err}")
    code = stdout.channel.recv_exit_status()
    print(f"\n  >>> {'OK' if code == 0 else f'FAIL (exit {code})'}")
    if code != 0 and abort_on_fail:
        print("*** ABORTING ***")
        sys.exit(1)
    return code, out


def gate(ok, msg):
    """Assert a condition or abort the script."""
    if not ok:
        print(f"\n*** GATE FAILED: {msg} — aborting ***")
        sys.exit(1)
    print(f"  GATE PASS: {msg}")
