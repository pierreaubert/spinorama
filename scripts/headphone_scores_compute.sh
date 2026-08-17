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

# Compute headphone preference scores (pre/post EQ) using the Rust autoeq binary.
#
# For each headphone, runs autoeq in QA mode to extract the pre-optimization
# and post-optimization Harman headphone scores. Results are written as JSON
# alongside the existing EQ files.
#
# Usage:
#   ./scripts/headphone_scores_compute.sh [--force]
#
# Requires:
#   - autoeq binary in PATH (from sotf/crates/autoeq)
#   - Python 3 with datas/ importable
#   - EQ files already computed by headphone_eqs_compute.sh

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
    echo "Build it with: cargo install autoeq"
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

echo "=== Headphone score computation ==="

total=0
computed=0
skipped=0
failed=0

while IFS='|' read -r name shape origin; do
    total=$((total + 1))

    hp_measurement_dir="${MEASUREMENTS_DIR}/${name}"
    hp_eq_dir="${EQ_DIR}/${name}"
    score_file="${hp_eq_dir}/autoeq_score.json"

    # Find the frequency response CSV
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

    # Skip if score already exists (unless --force)
    if [ "$FORCE" != "--force" ] && [ -f "$score_file" ]; then
        echo "SKIP ${name}: score already computed"
        skipped=$((skipped + 1))
        continue
    fi

    target=$(target_for_shape "$shape")
    echo "COMPUTE ${name} (shape=${shape}, target=$(basename "$target"))"

    mkdir -p "$hp_eq_dir"

    # Run autoeq with headphone-score loss in QA mode to extract scores
    output=$(autoeq \
        --curve "$curve_file" \
        --target "$target" \
        --loss headphone-score \
        --peq-model pk \
        -n 7 \
        --preset balanced \
        --qa 0.0 \
        2>&1) || {
        echo "  FAIL: score computation failed for ${name}"
        failed=$((failed + 1))
        continue
    }

    pre_score=$(echo "$output" | grep 'Headphone Score:' | sed -n '1s/.*Pre-Optimization Headphone Score: //p' || true)
    post_score=$(echo "$output" | grep 'Headphone Score:' | sed -n '2s/.*Post-Optimization Headphone Score: //p' || true)

    if [ -z "$pre_score" ] || [ -z "$post_score" ]; then
        echo "  FAIL: could not parse scores for ${name}"
        failed=$((failed + 1))
        continue
    fi

    printf '{"pre_score": %s, "post_score": %s}\n' "$pre_score" "$post_score" > "$score_file"
    echo "  OK: pre=${pre_score} post=${post_score}"

    computed=$((computed + 1))

done < <(get_headphone_shapes)

echo "=== Done: ${total} total, ${computed} computed, ${skipped} skipped, ${failed} failed ==="

if [ "$failed" -gt 0 ]; then
    exit 1
fi
exit 0
