#!/bin/sh
# Start TARS automatically every time the Pi powers on.
#   sh install-service.sh          install and start it now
#   sh install-service.sh remove   stop it and turn it off
set -e
cd "$(dirname "$0")"
DIR="$(pwd)"
PY="$HOME/tars-venv/bin/python3"
[ -x "$PY" ] || PY="$(command -v python3)"

if [ "$1" = "remove" ]; then
    sudo systemctl disable --now claude-tars 2>/dev/null || true
    sudo rm -f /etc/systemd/system/claude-tars.service
    sudo systemctl daemon-reload
    echo "TARS will no longer start at boot."
    exit 0
fi

[ -f tars.json ] || cp tars.example.json tars.json

sudo tee /etc/systemd/system/claude-tars.service >/dev/null <<UNIT
[Unit]
Description=Claude TARS
After=network-online.target sound.target
Wants=network-online.target

[Service]
User=$(id -un)
WorkingDirectory=$DIR
ExecStart=$PY -m tars --config tars.json
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now claude-tars
sleep 3
systemctl --no-pager --lines=5 status claude-tars || true
echo
echo "TARS now starts at every boot. Control page: http://$(hostname).local:8080"
echo "Useful:  sudo systemctl restart claude-tars    (after changing tars.json or a git pull)"
echo "         journalctl -u claude-tars -f          (watch its messages; Ctrl+C to stop watching)"
