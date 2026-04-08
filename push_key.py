"""Push SSH public key to Pi using password auth (paramiko). Run once after fresh flash."""

import os
from pi_ssh import get_config, get_password, connect_password

host, user, key_path = get_config()
password = get_password()
pubkey_path = key_path + ".pub"

if not os.path.exists(pubkey_path):
    print(f"ERROR: Public key not found at {pubkey_path}")
    raise SystemExit(1)

with open(pubkey_path) as f:
    pubkey = f.read().strip()

print(f"Connecting to {host} as {user}...")
c, t = connect_password(host, user, password)
print("Connected.")

cmds = [
    "mkdir -p ~/.ssh && chmod 700 ~/.ssh",
    f'grep -qxF "{pubkey}" ~/.ssh/authorized_keys 2>/dev/null || echo "{pubkey}" >> ~/.ssh/authorized_keys',
    "chmod 600 ~/.ssh/authorized_keys",
    "echo KEY_INSTALLED && hostname && cat ~/.ssh/authorized_keys | wc -l",
]

for cmd in cmds:
    _, stdout, stderr = c.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(f"  OUT: {out}")
    if err:
        print(f"  ERR: {err}")

t.close()
print("Done — key installed.")
