#!/bin/bash
set -e

Xvfb :99 -screen 0 1280x800x24 &
sleep 1

x11vnc -display :99 -nopw -forever -shared -rfbport 5900 &

websockify --web=/usr/share/novnc/ 6080 localhost:5900 &
sleep 1

# Mantem o jogo sempre disponivel: se o jogador sair (ESC), relanca
# automaticamente sem derrubar o Xvfb/x11vnc/websockify, evitando o
# erro "Failed to connect to downstream server" ao reconectar.
while true; do
    python techsecure_control_room.py || true
    sleep 1
done
