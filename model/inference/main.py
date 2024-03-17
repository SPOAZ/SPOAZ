from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from recommender.Recommender import Recommender
from google.cloud import storage, bigquery
from google.oauth2 import service_account 
from datetime import datetime
import pytz  

#BigQuery 클라이언트 설정 
key_path = 'YOUR_GCP_CLIENT_KEY_FILE_PATH'

credentials = service_account.Credentials.from_service_account_file(
    key_path, scopes=["https://www.googleapis.com/auth/cloud-platform"],
)

client = bigquery.Client(credentials=credentials, project=credentials.project_id)

#Cloud Storage에서 최신 model 파일 가져오기 
def get_latest_file(bucket_name, prefix):
    """GCS 버킷에서 가장 최신 파일의 이름을 가져오는 함수"""
    storage_client = storage.Client(credentials=credentials, project=credentials.project_id)
    blobs = storage_client.list_blobs(bucket_name, prefix=prefix)

    latest_blob = None
    latest_datetime = pytz.utc.localize(datetime.min)  # 수정

    for blob in blobs:
        if blob.updated > latest_datetime:
            latest_blob = blob
            latest_datetime = blob.updated

    return latest_blob

def download_blob(blob, destination_file_name):
    #GCS에서 파일을 다운로드하는 함수
    blob.download_to_filename(destination_file_name)
    print(f"Blob {blob.name} downloaded to {destination_file_name}.")


bucket_name = 'spoaz-model'
prefix = 'output/cpu/model/recommender_models/'  # 모델 파일들이 있는 폴더 경로

latest_blob = get_latest_file(bucket_name, prefix)
if latest_blob:
    destination_file_name =  latest_blob.name.split('/')[-1]  
    download_blob(latest_blob, destination_file_name)
else:
    print("No files found.")

class UserPlaylistInfo(BaseModel):
    user_id : str
    playlist_id : str
    
#BigQuery에서 사용자 플레이리스트의 track_ids 가져오기     
def get_user_history(user_id, playlist_id):
    
    query = f"""
        SELECT track_id
        FROM `ProjectName.DatasetName.playlist_tracks`
        WHERE user_id = '{user_id}' AND playlist_id = '{playlist_id}'
    """
    query_job = list(client.query(query))
    
    track_ids = [row['track_id'] for row in query_job]
    
    return track_ids
  

app = FastAPI()

model = Recommender()

@app.on_event("startup")
async def startup_event():
    # 모델 준비.
    model.prepare_model(
        model_path=  destination_file_name,
        tracks_path="YOUR_PLAYLIST_TRACKS.csv",
        ratings_path="YOUR_PLAYLIST_RATINGS.csv"
    )

@app.post("/playlist_rec")
async def recommend(user_id: UserPlaylistInfo, playlist_id:UserPlaylistInfo):
    # 추천을 수행하기 전에 모델이 준비되었는지 확인
    if model.tracks is None:
        raise HTTPException(status_code=503, detail="Model is not ready")

    try:
        track_ids = get_user_history(user_id, playlist_id)
        # 추천 수행
        result = model.predict(track_ids, top_n=10)
        return {"recommendations": result}
    except KeyError as e:
        # 특정 트랙이 데이터셋에 없는 경우
        raise HTTPException(status_code=404, detail=f"Track not found: {e}")

# 서버 실행
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 