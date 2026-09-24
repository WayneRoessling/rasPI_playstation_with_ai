#!/bin/bash
# Pi rootfs repair script — runs inside WSL2
# Fixes interrupted apt full-upgrade (dpkg partial install)
set -e

PIROOT="/mnt/wsl/PhysicalDrive3p2"

echo "=== Checking mount ==="
if [ ! -d "$PIROOT/etc" ]; then
    echo "ERROR: Pi rootfs not mounted at $PIROOT"
    echo "Available mounts:"
    ls /mnt/wsl/ 2>/dev/null || echo "No WSL mounts"
    exit 1
fi
echo "OK: Pi rootfs found at $PIROOT"

echo ""
echo "=== System info from Pi rootfs ==="
cat "$PIROOT/etc/os-release" | grep -E "NAME|VERSION"
echo ""

echo "=== Checking dpkg status ==="
ls "$PIROOT/var/lib/dpkg/updates/" 2>/dev/null
ls "$PIROOT/var/lib/dpkg/lock*" 2>/dev/null || echo "No dpkg locks"

echo ""
echo "=== Binding virtual filesystems for chroot ==="
mount --bind /proc "$PIROOT/proc"
mount --bind /sys "$PIROOT/sys"
mount --bind /dev "$PIROOT/dev"
mount --bind /dev/pts "$PIROOT/dev/pts"
echo "Done"

echo ""
echo "=== Running dpkg --configure -a inside chroot ==="
chroot "$PIROOT" /bin/bash -c "
export DEBIAN_FRONTEND=noninteractive
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

echo 'Configuring unconfigured packages...'
dpkg --configure -a 2>&1 || true

echo ''
echo 'Fixing any broken dependencies...'
apt-get install -f -y 2>&1 || true

echo ''
echo 'Updating initramfs for all kernels...'
update-initramfs -u -k all 2>&1 || true

echo ''
echo 'Verifying systemd...'
ls -la /usr/lib/systemd/systemd || echo 'WARNING: systemd binary not found'
/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1 /usr/lib/systemd/systemd --version 2>&1 | head -2 || echo 'systemd version check failed'

echo ''
echo 'Checking SSH daemon...'
ls -la /usr/sbin/sshd && echo 'sshd OK' || echo 'WARNING: sshd missing'

echo 'REPAIR COMPLETE'
"

echo ""
echo "=== Unmounting virtual filesystems ==="
umount "$PIROOT/dev/pts" 2>/dev/null || true
umount "$PIROOT/dev" 2>/dev/null || true
umount "$PIROOT/sys" 2>/dev/null || true
umount "$PIROOT/proc" 2>/dev/null || true
echo "Done"

echo ""
echo "=== REPAIR SCRIPT FINISHED ==="
echo "Eject the microSD and put it back in the Pi"
