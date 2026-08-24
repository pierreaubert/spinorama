#!/bin/sh
# A library to display spinorama charts
#
# Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# Lint every generated HTML file with w3c-html-validator.
#
# Environment overrides (optional):
#   W3C_VALIDATOR_URL  Validator endpoint (default: local Nu Validator at
#                     http://127.0.0.1:8889/). An explicit override is
#                     supported for development only.
#   W3C_DELAY_MS       Inter-request delay in milliseconds (default: 0 for
#                     the local validator).
#
# When using the default endpoint, this script starts/reuses the local Docker
# image `validator/validator`. It never calls validator.w3.org by default.

OS=$(uname)
status=0
files=""
LOCAL_VALIDATOR_URL=${LOCAL_VALIDATOR_URL:-http://127.0.0.1:8889/}
W3C_VALIDATOR_URL=${W3C_VALIDATOR_URL:-$LOCAL_VALIDATOR_URL}
W3C_DELAY_MS=${W3C_DELAY_MS:-0}

start_local_validator() {
    if test "$W3C_VALIDATOR_URL" != "$LOCAL_VALIDATOR_URL"; then
        return 0
    fi
    if ! command -v docker >/dev/null 2>&1; then
        echo "Local HTML validation requires Docker (validator/validator)." >&2
        return 1
    fi
    if ! docker container inspect --format '{{.State.Running}}' spinorama-nu-validator 2>/dev/null | grep -qx true; then
        docker rm -f spinorama-nu-validator >/dev/null 2>&1 || true
        if ! docker run -d --rm --name spinorama-nu-validator \
            -p 127.0.0.1:8889:8888 validator/validator:latest >/dev/null; then
            echo "Could not start the local Nu Validator container." >&2
            return 1
        fi
    fi

    attempts=0
    while test "$attempts" -lt 30; do
        if curl --fail --silent --output /dev/null "$LOCAL_VALIDATOR_URL?out=json"; then
            return 0
        fi
        attempts=$((attempts + 1))
        sleep 1
    done
    echo "Local Nu Validator did not become ready at $LOCAL_VALIDATOR_URL." >&2
    return 1
}

# Pre-filter: drop empty files and skip icons.html (intentionally untyped).
for d in dist/*.html; do
    sz=0
    if test "$OS" = "Linux"; then
        sz=$(stat -c %s "$d")
    elif test "$OS" = "Darwin"; then
        sz=$(stat -f "%z" "$d")
    fi
    if test "$sz" -eq 0; then
        status=1
        echo "$d is empty (ERROR)"
        continue
    fi
    test "$d" = "dist/icons.html" && continue
    files="$files $d"
done

if test -z "$files"; then
    test $status -eq 0 && echo "no files to lint" && exit 0
    exit 1
fi

validation_cache="${HTML_VALIDATION_CACHE:-.cache/html-validation.manifest}"
validation_key="validator=${W3C_VALIDATOR_URL};delay=${W3C_DELAY_MS}"
for d in $files; do
    if test "$OS" = "Linux"; then
        mtime=$(stat -c "%Y" "$d")
        size=$(stat -c "%s" "$d")
    elif test "$OS" = "Darwin"; then
        mtime=$(stat -f "%m" "$d")
        size=$(stat -f "%z" "$d")
    fi
    validation_key="$validation_key|$d:$mtime:$size"
done

if test "${CHECK_HTML_FORCE:-0}" != "1" && test -f "$validation_cache"; then
    cached_key=$(cat "$validation_cache")
    if test "$cached_key" = "$validation_key"; then
        echo "HTML validation cache hit"
        exit 0
    fi
fi

if ! start_local_validator; then
    exit 1
fi

opts="--continue --delay=${W3C_DELAY_MS} --check-url=$W3C_VALIDATOR_URL"

# A single invocation processes every file with the validator's internal
# throttling (`--delay`), so we hit the endpoint at most one rate-controlled
# stream rather than launching one Node process per file.
# shellcheck disable=SC2086
if ! ./node_modules/.bin/w3c-html-validator $opts $files; then
    status=1
fi

if test $status -eq 0; then
    mkdir -p "$(dirname "$validation_cache")"
    printf '%s\n' "$validation_key" > "$validation_cache"
    echo "all files are clean!"
    exit 0
else
    exit 1
fi
