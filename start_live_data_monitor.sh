#!/bin/bash

# .env 파일들을 읽어 환경변수로 설정합니다.
set -o allexport
source .env
set +o allexport

# Run the market monitor
ttnw/bin/python workers/market_monitor.py > logs/market_monitor.log 2>&1 &
