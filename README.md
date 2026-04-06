# Backend 개발환경 세팅 가이드

## 개발환경 기준

이 프로젝트는 아래 환경을 기준으로 개발합니다.

- Python **3.11.x**
  - 권장: **3.11.5**
- Django **5.2.12**
- Django REST framework **3.16.1**
- 가상환경: `venv`

---

## 1. 프로젝트 클론 후 폴더 이동

```bash
git clone <저장소 주소>
cd <프로젝트 폴더>
```

---

## 2. .env 생성 및 환경변수 입력

프로젝트 루트에 .env 파일을 생성하고 아래 환경변수 값을 입력합니다.

```text
SECRET_KEY = {YOUR_DJANGO_SECRET_KEY}
DEBUG = True

DB_NAME={YOUR_DB_NAME}
DB_USER={YOUR_DB_USER}
DB_PASSWORD={YOUR_DB_PASSWORD}
DB_HOST={YOUR_DB_HOST}
DB_PORT={YOUR_DB_PORT}

FASTAPI_BASE_URL=http://localhost:8000
```

---

## 3. 가상환경 생성

프로젝트 루트에서 아래 명령어를 실행합니다.

```bash
python -m venv .venv
```

---

## 4. 가상환경 활성화

사용 중인 터미널에 따라 아래 명령어를 사용합니다.

### Git Bash

```bash
source .venv/Scripts/activate
```

### PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

### CMD

```cmd
.venv\Scripts\activate.bat
```

가상환경이 정상적으로 활성화되면 터미널 앞에 `(.venv)`가 표시됩니다.

예시:

```bash
(.venv) user@PC MINGW64 /c/workspace/project/backend
```

---

## 5. pip 업데이트

```bash
python -m pip install --upgrade pip
```

---

## 6. 필수 패키지 설치

현재 프로젝트의 기본 패키지는 아래와 같습니다.

```bash
python -m pip install Django==5.2.12 djangorestframework==3.16.1 mysqlclient==2.2.8 python-dotenv==1.2.2
```

## 7. 작업 종료 후 가상환경 비활성화

```bash
deactivate
```

---
