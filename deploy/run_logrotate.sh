#!/bin/sh
set -eu

trap 'exit 0' INT TERM

while true; do
    logrotate --state /var/lib/logrotate/status /etc/logrotate.conf
    sleep 900 &
    wait $! || true
done
