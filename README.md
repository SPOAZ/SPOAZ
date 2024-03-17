# Spotify 기반 개인화 음악추천 챗봇서비스 개발 프로젝트

Project Overview
---
본 프로젝트에서는 Spotify 데이터를 사용하여 트랙, 플레이리스트, 무드 기반 등 다양한 개인화 음악 추천 및 검색 서비스를 위한 챗봇 웹 프로덕트를 제작하였습니다.

1. 서비스 소개 <br/>
   사용자의 다양한 음악적 취향과 요구를 충족시키기 위해 세 가지 유형의 음악추천 서비스를 기획하였습니다. 
   ![스크린샷 2024-02-27 오후 3 06 29](https://github.com/SPOAZ/SPOAZ/assets/84179278/af6d164c-86a1-413e-87e0-b1f7e594ace5)
  
   
3. 프로젝트 핵심 Task 소개
- 추천 시스템 모델을 위한 GCP 클라우드 기반 Feature Engineering 환경 구축
  - Online/Offline Feature Store : BigQuery
  - Offline Feature Engineering Pipeline Orchestration: Apache Airflow
  - Online Feature Engineering Pipeline: GCP Cloud Function, Cloud Pub/Sub
  - Online/Offline Feature Store Sync Pipeline : Apache Airflow
    
- GCP Vertex AI 플랫폼 기반 MLOps 환경 구축
    - 사용자 플레이리스트 기반 노래 추천 서비스 구현을 위한 BERT4Rec 모델 학습 파이프라인 구축
    - 모델 학습 파이프라인: GCP Vertex AI Custom Model Training Pipeline
    - Dataset: Spotify Playlist Dataset (사용자 1074명, Track 23924개)
    - 모델 배포 컨테이너: GCP Artifact Registry
    - 모델 서빙 : Artifact Registry의 Inference 컨테이너를 Cloud Run 배포(Serverless)


프로젝트 워크플로우 및 파이프라인
---
![스크린샷 2024-02-27 오후 2 42 04](https://github.com/SPOAZ/SPOAZ/assets/84179278/903ac3e4-e8ce-4c02-9065-584e112c6b8b)

Member
---
- 서울여자대학교 소프트웨어융합학과 안소유  <a href="https://sososoy.tistory.com/" target="_blank"><img src="https://img.shields.io/badge/Tistory-000000?style=for-the-badge&logo=Tistory&logoColor=white"></a>
- 중앙대학교 응용통계학과 임혁  <a href="https://harveywoods.tistory.com/" target="_blank"><img src="https://img.shields.io/badge/Tistory-000000?style=for-the-badge&logo=Tistory&logoColor=white"></a>
- 서울여자대학교 소프트웨어융합학과 이해현  <a href="https://chrissarchive.oopy.io/" target="_blank"><img src="https://img.shields.io/badge/Velog-20C997?style=flat-square&logo=velog&logoColor=white"></a>









