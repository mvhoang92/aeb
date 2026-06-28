#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AEB_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CARLA_ROOT="$(cd "${AEB_ROOT}/.." && pwd)"
PYTHON_BIN="${CARLA_ROOT}/venv/bin/python"

SPLIT="${1:-train}"
SESSIONS="${2:-5}"
SAMPLES_PER_SESSION="${3:-50}"
CARS="${4:-4}"
SEED_BASE="${5:-2100}"
CONFIG_PATH="${AEB_ROOT}/configs/dataset_collection_v7_same_lane.yaml"
STAMP="$(date +%Y%m%d_%H%M%S)"

cd "${AEB_ROOT}"

echo "Collect v7 same-lane dataset"
echo "  split              : ${SPLIT}"
echo "  sessions           : ${SESSIONS}"
echo "  samples/session    : ${SAMPLES_PER_SESSION}"
echo "  same-lane cars     : ${CARS}"
echo "  config             : ${CONFIG_PATH}"
echo

for index in $(seq 1 "${SESSIONS}"); do
  seed=$((SEED_BASE + index))
  session_id="town04_${SPLIT}_v7_same_lane_${CARS}cars_${STAMP}_$(printf "%02d" "${index}")"
  echo "=== Session ${index}/${SESSIONS}: ${session_id} | seed=${seed} ==="
  "${PYTHON_BIN}" -u scripts/collect_yolo_dataset.py \
    --config "${CONFIG_PATH}" \
    --split "${SPLIT}" \
    --session-id "${session_id}" \
    --max-samples "${SAMPLES_PER_SESSION}" \
    --number-of-vehicles "${CARS}" \
    --same-lane-vehicles "${CARS}" \
    --seed "${seed}" \
    --no-window
  echo
done
