#!/usr/bin/env bash
# scripts/run_golden.sh — Run Python golden model tests
set -euo pipefail

cd "$(dirname "$0")/../golden"
python test_ntt.py
