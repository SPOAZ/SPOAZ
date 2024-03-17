# 기본 이미지 선택
FROM --platform=linux/amd64 python:3.8-slim

# 필요한 라이브러리 설치
RUN pip install google-cloud-bigquery kfp pandas

# 필요한 경우 추가적인 설정
COPY . /app
WORKDIR /app