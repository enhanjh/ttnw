#!/bin/bash
# ttnw 프로젝트의 Celery 워커를 시작하는 스크립트입니다.

# .env 파일들을 읽어 환경변수로 설정합니다.
set -o allexport
source .env
set +o allexport

echo "Starting Celery worker..."

# 로그를 남기며 백그라운드에서 워커 실행
/opt/ttnw/ttnw/bin/celery -A workers.celery_app.app worker --loglevel=INFO -c 1 > logs/worker.log 2>&1 &