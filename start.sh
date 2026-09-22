#!/bin/bash
set -e

Xvfb :99 -screen 0 1280x800x24 &
sleep 1

x11vnc -display :99 -nopw -forever -shared -rfbport 5900 &

websockify --web=/usr/share/novnc/ 6080 localhost:5900 &
sleep 1

python techsecure_control_room.py
