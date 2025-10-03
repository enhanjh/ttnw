# Portfolio Manager Web Application Development Summary

This document summarizes the development steps taken to create the Portfolio Manager web application. It covers the initial plan, the evolution of the tech stack (from SQLite to MongoDB and serverless), and detailed procedures for local testing and deployment.

## 1. Initial Development Plan

포트폴리오 수익률 관리 및 백테스팅 웹 프로그램 개발 계획:

*   **목표:** 사용자가 자신의 포트폴리오를 등록하고 수익률을 관리하며, 다양한 투자 전략을 과거 데이터에 기반하여 백테스팅할 수 있는 웹 기반 애플리케이션 개발.
*   **기술 스택 (초기 제안):**
    *   **프론트엔드:** React, Chart.js
    *   **백엔드:** Python (FastAPI), Pandas, yfinance
    *   **데이터베이스:** SQLite

## 2. Evolution of the Architecture

### 2.1. Database Migration: SQLite to MongoDB

초기에는 빠른 프로토타이핑을 위해 SQLite를 사용했으나, 확장성과 유연성을 고려하여 NoSQL 데이터베이스인 MongoDB로 마이그레이션을 결정했습니다.

*   **ORM 변경**: SQLAlchemy에서 `Beanie` (Asynchronous ODM for MongoDB)로 변경하여 비동기 FastAPI 환경과의 호환성을 높였습니다.
*   **데이터 이전**: 기존 SQLite(`portfolio.db`)의 모든 데이터를 MongoDB Atlas로 이전하기 위해 일회성 마이그레이션 스크립트(`migration_sqlite_to_mongo.py`)를 작성하여 실행했습니다.

### 2.2. Deployment Strategy: From Monolithic to Serverless

초기 배포 전략은 단일 서버에 uvicorn/gunicorn을 배포하는 것이었으나, 비용 효율성과 확장성을 극대화하기 위해 AWS 서버리스 아키텍처를 채택하기로 결정했습니다.

*   **백엔드**: AWS Lambda와 API Gateway를 사용하여 트래픽에 따라 자동으로 확장되는 API를 구성합니다.
*   **프론트엔드**: AWS S3와 CloudFront를 사용하여 전 세계 사용자에게 빠르고 안정적으로 정적 파일을 제공합니다.
*   **자동화**: Serverless Framework를 도입하여 간단한 `serverless.yml` 파일로 전체 클라우드 인프라를 코드로서 관리(IaC)하고 배포를 자동화합니다.

## 3. Project Setup

### Final Directory Structure
```
portfolio_manager/
├── backend/
│   ├── .env
│   ├── main.py
│   ├── serverless.yml
│   └── ...
├── frontend/
│   ├── .env
│   ├── serverless.yml
│   └── ...
├── ttnw/ (Python Virtual Environment)
└── requirements.txt
```

### Final Dependencies (`requirements.txt`)
```
fastapi==0.111.0
uvicorn==0.30.1
pandas==2.2.2
numpy==1.26.4
yfinance==0.2.40
beanie==1.26.0
motor==3.1.2
pymongo==4.3.3
mangum==0.17.0
python-dotenv==1.0.1
```

## 4. Environment Variable Management (Local vs. Production)

이 프로젝트는 로컬 개발 환경과 배포 환경의 설정을 분리하여 관리합니다. 핵심은 민감한 정보나 환경별 설정이 담긴 `.env` 파일을 로컬 개발용으로만 사용하고, Git 저장소에는 포함하지 않는 것입니다. (`.gitignore`에 `**/.env` 규칙이 설정되어 있습니다.)

| 환경 | 백엔드 (`DATABASE_URL`) | 프론트엔드 (`REACT_APP_API_URL`) |
| :--- | :--- | :--- |
| **로컬 개발** | `backend/.env` 파일에서 로드 | `frontend/.env` 파일에서 로드 |
| **클라우드 배포** | `serverless deploy` 명령어의 `--param`으로 주입 | `npm run build` 명령어의 접두사로 주입 |

### Backend (`DATABASE_URL`)
*   **로컬**: `uvicorn` 실행 시 `main.py`의 `load_dotenv()` 코드가 `backend/.env` 파일을 읽어 DB 연결 문자열을 환경 변수로 설정합니다.
*   **배포**: `backend/serverless.yml`의 `${param:db_url}` 설정에 따라, `serverless deploy` 명령어에 `--param`으로 전달된 실제 운영 DB의 주소가 Lambda 함수의 환경 변수로 안전하게 주입됩니다.

### Frontend (`REACT_APP_API_URL`)
*   **로컬**: `npm start` 실행 시 React는 `frontend/.env` 파일을 읽어 로컬 백엔드 주소(`http://localhost:8000`)를 사용합니다.
*   **배포**: `REACT_APP_API_URL=<운영-API-주소> npm run build` 명령어를 통해, 생성되는 정적 파일에 실제 운영 API 주소가 포함되도록 합니다. 이 값은 로컬 `.env` 파일의 설정을 덮어씁니다.

## 5. Local Development and Testing

클라우드에 배포하기 전, 로컬 환경에서 전체 시스템을 테스트하는 절차입니다.

### 1. Database Setup
*   **MongoDB Atlas** 클라우드 데이터베이스를 그대로 사용합니다.
*   [MongoDB Atlas Network Access](https://cloud.mongodb.com/v2#/orgs/<ORG_ID>/projects/<PROJECT_ID>/network/access) 메뉴에서 `Add IP Address` -> `Allow Access From My Current IP Address`를 선택하여 로컬 장비의 IP를 허용 목록에 추가합니다.

### 2. Backend Execution
1.  `backend` 폴더로 이동합니다.
2.  가상 환경을 활성화합니다: `source ../ttnw/bin/activate` (macOS) 또는 `..\ttnw\Scripts\activate` (Windows).
3.  `backend` 폴더에 `.env` 파일을 생성하고, MongoDB Atlas 연결 문자열을 추가합니다.
    ```
    DATABASE_URL="<YOUR_MONGODB_ATLAS_CONNECTION_STRING>"
    ```
4.  `uvicorn`으로 로컬 개발 서버를 실행합니다. `main.py`의 `load_dotenv()`가 `.env` 파일을 자동으로 읽습니다.
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    ```

### 3. Frontend Execution
1.  `frontend` 폴더로 이동합니다.
2.  `frontend` 폴더에 `.env` 파일을 생성하고, 로컬 백엔드 주소를 다음과 같이 입력합니다.
    ```
    REACT_APP_API_URL=http://localhost:8000
    ```
3.  `npm install`로 의존성을 설치한 후, `npm start`로 React 개발 서버를 실행합니다.

### 4. Automated Start & Stop (Recommended)
*   **서버 시작**:
    *   위의 2, 3번 과정을 자동화하는 `start_test_server.sh` 스크립트가 프로젝트 루트에 있습니다.
    *   각 폴더에 `.env` 파일들을 준비한 후, 루트 디렉토리에서 `./start_test_server.sh`를 실행하면 백엔드와 프론트엔드 서버가 동시에 시작됩니다.
*   **서버 중지**:
    *   서버를 중지하려면, 스크립트를 실행한 터미널에서 `Ctrl+C`를 누르기만 하면 됩니다.
    *   스크립트 내에 두 서버를 모두 안전하게 종료하는 로직이 포함되어 있어 별도의 중지 스크립트는 필요하지 않습니다.

## 6. Deployment

### 6.1. Serverless Deployment on AWS (Recommended)

Serverless Framework를 사용한 자동화된 배포 방법입니다.

#### Prerequisites
1.  **AWS CLI & Serverless Framework**: `aws configure`로 AWS 계정을 설정하고, `npm install -g serverless`로 프레임워크를 설치합니다.
2.  **MongoDB Atlas**: 클라우드 DB를 준비하고 연결 문자열을 복사합니다.

#### Backend Deployment (Lambda + API Gateway)
1.  `backend` 폴더로 이동합니다.
2.  플러그인을 설치합니다: `serverless plugin install -n serverless-python-requirements`
3.  아래 명령어로 배포합니다. `<...>` 부분은 실제 MongoDB 연결 문자열로 교체합니다.
    ```bash
    serverless deploy --param="db_url=<YOUR_MONGODB_ATLAS_CONNECTION_STRING>"
    ```
4.  배포 완료 후 출력되는 `endpoint` 주소를 복사합니다.

#### Frontend Deployment (S3)
1.  `frontend` 폴더로 이동합니다.
2.  플러그인을 설치합니다: `serverless plugin install -n serverless-s3-sync`
3.  백엔드 `endpoint` 주소를 환경 변수로 설정하여 React 앱을 빌드합니다.
    ```bash
    REACT_APP_API_URL=<YOUR_BACKEND_ENDPOINT_URL> npm run build
    ```
4.  `serverless deploy` 명령어로 빌드된 파일을 S3에 배포합니다.
5.  배포 완료 후 출력되는 S3 웹사이트 주소로 접속하여 확인합니다.

### 6.2. Simple Deployment on a Single Server (Alternative)

단일 Windows 서버에 배포하는 더 전통적인 방법입니다.

1.  **Database**: MongoDB를 Windows 서비스로 설치합니다.
2.  **Frontend**: `npm run build`로 생성된 `build` 폴더의 내용을 백엔드 `static` 폴더로 복사합니다.
3.  **Backend**: FastAPI가 정적 파일을 직접 서빙하도록 `main.py`를 수정합니다. (현재 코드는 서버리스에 최적화되어 있으므로, 필요 시 재구현해야 합니다.)
4.  **Execution**: `NSSM`과 같은 도구를 사용하여 `uvicorn` 프로세스를 Windows 서비스로 등록하여 실행합니다.

## 7. Further Enhancements (Future Work)

*   Implement more sophisticated backtesting strategies.
*   Enhance data visualization with more chart types and interactive features.
*   Add user authentication and portfolio management per user.
*   Integrate with more real-time data sources.
*   Implement portfolio optimization algorithms.
