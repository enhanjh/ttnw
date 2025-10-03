# Python 3.12 슬림 이미지 사용
FROM python:3.12-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (필요한 경우 git, gcc 등 추가)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 전체 복사
COPY . .

# Python path 설정 (현재 디렉토리를 모듈 경로에 추가)
ENV PYTHONPATH=/app

# 실행 명령어는 docker-compose에서 오버라이드 됨
CMD ["python", "backend/main.py"]
