#!/bin/sh
set -eu

while :; do
    if psql -X -v ON_ERROR_STOP=1 -h db -U "$PGUSER" -d "$PGDATABASE" \
        -c 'SELECT public.gridwatch_apply_measurement_retention()'; then
        echo 'GridWatch retention check completed.'
    else
        echo 'GridWatch retention check failed; will retry in one hour.' >&2
        sleep 3600
        continue
    fi
    sleep 86400
done
