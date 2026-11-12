#!/bin/sh
set -eu
# Aman dijalankan berulang: init-db tidak menghapus data yang sudah ada.
python -m flask --app app init-db
exec gunicorn app:app --bind "0.0.0.0:${PORT:-10000}" --workers 2 --timeout 90
