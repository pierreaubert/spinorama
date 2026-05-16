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
#   W3C_VALIDATOR_URL  Validator endpoint (default: https://validator.w3.org/nu/).
#                     Point at a local Nu validator (Docker
#                     `validator/validator` or vnu.jar) to avoid the public
#                     service's rate-limiting (`403 Forbidden` after a few
#                     dozen requests).
#                     e.g. W3C_VALIDATOR_URL=http://localhost:8888/
#   W3C_DELAY_MS       Inter-request delay in milliseconds (default: 2000).
#                     Only relevant when hitting the public W3C endpoint.

OS=$(uname)
status=0
files=""

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

opts="--continue --delay=${W3C_DELAY_MS:-2000}"
if test -n "$W3C_VALIDATOR_URL"; then
    opts="$opts --check-url=$W3C_VALIDATOR_URL"
fi

# A single invocation processes every file with the validator's internal
# throttling (`--delay`), so we hit the endpoint at most one rate-controlled
# stream rather than launching one Node process per file.
# shellcheck disable=SC2086
if ! ./node_modules/.bin/w3c-html-validator $opts $files; then
    status=1
fi

if test $status -eq 0; then
    echo "all files are clean!"
    exit 0
else
    exit 1
fi
