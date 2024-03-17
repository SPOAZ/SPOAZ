# 베이스 이미지를 python 3.8로 설정합니다.
FROM --platform=linux/amd64 python:3.8-slim

# 작업 디렉토리를 설정합니다.
WORKDIR /app

# 필요한 Python 라이브러리를 설치합니다.
COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드를 컨테이너로 복사합니다.
COPY . .


# 서비스를 실행합니다.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]