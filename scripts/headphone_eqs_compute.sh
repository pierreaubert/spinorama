#!/bin/bash
# A library to display spinorama charts
#
# Copyright (C) 2020-2026 Pierre Aubert pierre(at)spinorama(dot)org
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

# Compute EQ filters for headphones using the Rust autoeq binary.
#
# For each headphone measurement directory, run autoeq with the correct
# Harman target curve (over-ear or in-ear) based on metadata.
#
# Usage:
#   ./scripts/headphone_eqs_compute.sh [--force]
#
# Requires:
#   - autoeq binary in PATH (from sotf/crates/autoeq)
#   - Python 3 with datas/ importable

set -euo pipefail

FORCE="${1:-}"
THEPYTHON="${THEPYTHON:-python3.12}"

MEASUREMENTS_DIR="datas/headphones"
EQ_DIR="datas/headphone_eq"
TARGETS_DIR="datas/headphone_targets"

TARGET_OVEREAR="${TARGETS_DIR}/harman_overear_2019.csv"
TARGET_INEAR="${TARGETS_DIR}/harman_inear_2019.csv"

# Check autoeq binary
if ! command -v autoeq &> /dev/null; then
    echo "ERROR: autoeq binary not found in PATH"
    echo "Build it with: cd ../sotf && cargo build --release -p autoeq"
    exit 1
fi

# Check target files exist
for t in "$TARGET_OVEREAR" "$TARGET_INEAR"; do
    if [ ! -f "$t" ]; then
        echo "ERROR: Target curve not found: $t"
        exit 1
    fi
done

# Get the shape for each headphone from Python metadata
# Outputs lines like: "Brand Model|over-ear"
get_headphone_shapes() {
    ${THEPYTHON} -c "
import sys
sys.path.insert(0, 'src')
sys.path.insert(0, '.')
try:
    from datas.headphones import headphones_info
except ImportError:
    print('ERROR: Cannot import headphones', file=sys.stderr)
    sys.exit(1)

for name, info in headphones_info.items():
    if info.get('skip', False):
        continue
    shape = info.get('shape', 'over-ear')
    origin = info.get('default_measurement', 'asr')
    print(f'{name}|{shape}|{origin}')
"
}

# Select target curve based on shape
target_for_shape() {
    local shape="$1"
    case "$shape" in
        in-ear|earbud)
            echo "$TARGET_INEAR"
            ;;
        *)
            echo "$TARGET_OVEREAR"
            ;;
    esac
}

echo "=== Headphone EQ computation ==="

total=0
computed=0
skipped=0
failed=0

while IFS='|' read -r name shape origin; do
    total=$((total + 1))

    hp_measurement_dir="${MEASUREMENTS_DIR}/${name}"
    hp_eq_dir="${EQ_DIR}/${name}"

    # Find the frequency response CSV (inside the measurement origin subdir)
    curve_file=""
    for origin_dir in "$origin" "asr"; do
        for candidate in "${hp_measurement_dir}/${origin_dir}/frequency_response.csv" \
                         "${hp_measurement_dir}/${origin_dir}/freq_response.csv" \
                         "${hp_measurement_dir}/${origin_dir}/fr.csv"; do
            if [ -f "$candidate" ]; then
                curve_file="$candidate"
                break 2
            fi
        done
    done

    if [ -z "$curve_file" ]; then
        echo "SKIP ${name}: no frequency response CSV found"
        skipped=$((skipped + 1))
        continue
    fi

    # Skip if EQ already exists (unless --force)
    if [ "$FORCE" != "--force" ] && [ -f "${hp_eq_dir}/iir-autoeq-score.txt" ]; then
        echo "SKIP ${name}: EQ already computed"
        skipped=$((skipped + 1))
        continue
    fi

    target=$(target_for_shape "$shape")
    echo "COMPUTE ${name} (shape=${shape}, target=$(basename "$target"))"

    mkdir -p "$hp_eq_dir"

    # Run autoeq with headphone-score loss (Harman preference)
    if autoeq \
        --curve "$curve_file" \
        --target "$target" \
        --loss headphone-score \
        --peq-model pk \
        -n 7 \
        --preset balanced \
        --output "${hp_eq_dir}/autoeq_score" \
        2>&1 | tail -3; then
        echo "  OK: score EQ computed"
    else
        echo "  FAIL: score EQ failed for ${name}"
        failed=$((failed + 1))
        continue
    fi

    # Also run with headphone-flat loss (minimum deviation)
    if autoeq \
        --curve "$curve_file" \
        --target "$target" \
        --loss headphone-flat \
        --peq-model pk \
        -n 7 \
        --preset balanced \
        --output "${hp_eq_dir}/autoeq_flat" \
        2>&1 | tail -3; then
        echo "  OK: flat EQ computed"
    else
        echo "  WARN: flat EQ failed for ${name} (non-fatal)"
    fi

    computed=$((computed + 1))

done < <(get_headphone_shapes)

echo "=== Done: ${total} total, ${computed} computed, ${skipped} skipped, ${failed} failed ==="

if [ "$failed" -gt 0 ]; then
    exit 1
fi
exit 0
