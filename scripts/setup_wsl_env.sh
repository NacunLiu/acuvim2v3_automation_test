#!/usr/bin/env bash
# Initial one-time WSL environment setup for the Jenkins CI/CD pipeline.
# Run once as a user with sudo access: bash scripts/setup_wsl_env.sh
set -euo pipefail

echo "=== Installing system packages ==="
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip python3-venv python3-dev \
    nmap libopencv-dev scrot

echo "=== Adding jenkins user to dialout (serial port access) ==="
sudo usermod -aG dialout jenkins

echo "=== Enabling WSL mirrored networking for Kasa LAN access ==="
WSLCONFIG="${WSLCONFIG:-/mnt/c/Users/$(cmd.exe /c 'echo %USERNAME%' 2>/dev/null | tr -d '\r\n')/.wslconfig}"
if grep -q "networkingMode" "$WSLCONFIG" 2>/dev/null; then
    echo "  .wslconfig already has networkingMode, skipping"
else
    cat >> "$WSLCONFIG" <<'EOF'

[wsl2]
networkingMode=mirrored
EOF
    echo "  Written to $WSLCONFIG — run 'wsl --shutdown' from PowerShell then reopen WSL"
fi

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. From PowerShell: wsl --shutdown   (applies mirrored networking)"
echo "  2. Reopen WSL terminal"
echo "  3. Install usbipd-win on Windows for USB serial sharing:"
echo "     winget install usbipd  (run in Windows PowerShell as Admin)"
echo "  4. After usbipd install, attach USB serial adapter to WSL:"
echo "     usbipd list            (find bus ID of your USB-Serial adapter)"
echo "     usbipd attach --wsl --busid <busid>"
echo "  5. Verify adapter visible in WSL: ls /dev/ttyUSB*"
