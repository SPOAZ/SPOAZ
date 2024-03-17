from google.cloud import bigquery
import base64
import json

# BigQuery 클라이언트 초기화
client = bigquery.Client()

def pubsub_to_bigquery(event, context):
    """Pub/Sub 메시지를 받아 BigQuery에 적재하는 Cloud Function"""
    
    # Pub/Sub 메시지 파싱
    if 'data' in event:
        message_data = base64.b64decode(event['data']).decode('utf-8')
        playlist = json.loads(message_data)
    
    # BigQuery 테이블 참조
    playlist_table_id = "GCP_PROJECT_NAME.OnlineStore.playlist_tracks"
    dictionary_table_id = "GCP_PROJECT_NAME.OnlineStore.playlist_track_dictionary"
    
    # 테이블 객체 가져오기
    playlist_table = client.get_table(playlist_table_id)
    dictionary_table = client.get_table(dictionary_table_id)
    
    # 레코드 생성
    p_row = (
        playlist['user_id'],  
        playlist['playlist_id'],
        playlist['track_id'],
        playlist['timestamp'],
        playlist['ratings']
    )
    
    d_row = (
        playlist['track_id'],
        playlist['title']
    )
    
    # BigQuery에 삽입
    p_errors = client.insert_rows(playlist_table, [p_row])
    d_errors = client.insert_rows(dictionary_table, [d_row])
  
    if p_errors != []:
        raise Exception(f"BigQuery insertion error: {p_errors}")
    
    if d_errors != []:
        raise Exception(f"BigQuery insertion error: {d_errors}")
