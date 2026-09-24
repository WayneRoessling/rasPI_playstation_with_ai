"""Quick system state check — SSH into Pi, print key diagnostics."""

from pi_ssh import connect, run

client = connect()

run(client, "uname -r", label="kernel")
run(client, "free -h | head -2", label="RAM")
run(client, "df -h / | tail -1", label="disk")
run(client, "which git curl ffmpeg htop tmux && echo TOOLS_OK", label="tools check")
# OpenCV is pip-installed in the venv (apt python3-opencv segfaults), not system python3
run(client, '~/mini-ai/.venv/bin/python -c "import cv2; print(cv2.__version__)" 2>&1', label="opencv", abort_on_fail=False)
run(client, "grep gpu_mem /boot/firmware/config.txt 2>/dev/null || echo NOT_SET", label="gpu_mem")
run(client, "lsmod | grep i2c_dev && echo I2C_LOADED || echo I2C_NOT_LOADED", label="i2c module")
run(client, "ls /dev/i2c* 2>/dev/null || echo NO_I2C_DEV", label="i2c devices")
run(client, "ls /dev/spidev* 2>/dev/null || echo NO_SPI_DEV", label="spi devices")
run(client, "vcgencmd version 2>/dev/null || echo vcgencmd-unavailable", label="firmware")

client.close()
print("CHECK DONE")
