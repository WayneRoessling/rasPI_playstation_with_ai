"""Find Pi by scanning candidates, push SSH key, update .env with new IP."""

import os
from pi_ssh import get_config, get_password, connect_password

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(_SCRIPT_DIR, ".env")

host, user, key_path = get_config()
password = get_password()
pubkey_path = key_path + ".pub"

CANDIDATES = [host]  # extend with more IPs if Pi moves

with open(pubkey_path) as f:
    pubkey = f.read().strip()

found_ip = None
for ip in CANDIDATES:
    try:
        print(f"Trying {ip}...")
        c, t = connect_password(ip, user, password)
        _, out, _ = c.exec_command("hostname && uname -r", timeout=8)
        info = out.read().decode().strip()
        print(f"  Connected! {info}")
        if "mini-ai" in info:
            found_ip = ip
            for cmd in [
                "mkdir -p ~/.ssh && chmod 700 ~/.ssh",
                f'grep -qxF "{pubkey}" ~/.ssh/authorized_keys 2>/dev/null || echo "{pubkey}" >> ~/.ssh/authorized_keys',
                "chmod 600 ~/.ssh/authorized_keys",
                "echo KEY_INSTALLED",
            ]:
                _, o, _ = c.exec_command(cmd, timeout=8)
                r = o.read().decode().strip()
                if r:
                    print(f"  {r}")
        t.close()
        if found_ip:
            break
    except Exception as e:
        print(f"  {e}")

if found_ip:
    print(f"\nPi found at {found_ip} — updating .env")
    if os.path.exists(ENV_PATH):
        lines = open(ENV_PATH).readlines()
        with open(ENV_PATH, "w") as f:
            for line in lines:
                if line.startswith("MINI_AI_HOST="):
                    f.write(f"MINI_AI_HOST={found_ip}\n")
                else:
                    f.write(line)
    print("Done.")
else:
    print("\nPi not found on any candidate IP.")
