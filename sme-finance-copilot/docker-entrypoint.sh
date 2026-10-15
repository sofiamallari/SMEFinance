#!/bin/sh
set -eu
if [ "$(id -u)" = "0" ]; then
  mkdir -p /data
  chown -R appuser:appuser /data
  exec setpriv --reuid=appuser --regid=appuser --init-groups "$@"
fi
exec "$@"
