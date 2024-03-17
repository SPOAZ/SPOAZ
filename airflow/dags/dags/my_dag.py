from airflow import DAG
from airflow.operators.python import PythonOperator

from datetime import datetime, timedelta
from dags.data_extractor import DataExtractor

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.providers.google.cloud.hooks.bigquery import BigQueryHook


import json 

import glob
from google.cloud import bigquery


# bigquery 테이블로부터 user_id, playlist_id 받아오기
def get_userinfo_from_biqquery(**kwargs):
    project_id = "wired-epsilon-409307"
    
    bigquery_hook = BigQueryHook(
        bigquery_conn_id = "google_cloud_default",
        use_legacy_sql = True,
        location="asia-northeast3",
        priority="INTERACTIVE"
    )

    sql = "SELECT * FROM OnlineStore.user_playlist_info"
    
    connection = bigquery_hook.get_conn()
    cursor = connection.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()

    df = [row for row in rows] # [[user_id, playlist_id]] 획득?
    return df

#TODO: streamlit에 접목시키기

cid = '4f57899d0d274464b9a0b34637b87022'
secret = 'faba1f2648d640d989e4c5b3867cbb82'

auth_manager = SpotifyClientCredentials(cid, secret)
sp = spotipy.Spotify(auth_manager=auth_manager)

bigquery_location = "asia-northeast3"


# 일주일 단위로 기존 플레이리스트의 곡 가져오기
def get_playlist(): # user_id, playlist_id
    user_data = get_userinfo_from_biqquery() # dataframe 획득

    playlist_dict = {}
    extract_info_dict = {}

    for info in user_data:
        playlist = sp.user_playlist(info[0], info[1]) # 플레이리스트 원본
        extract_info = DataExtractor(playlist).extract_track() # model 학습용 곡 정보 가져오기

        playlist_dict[info[0]] = playlist
        extract_info_dict[info[1]] = extract_info
    
    return playlist_dict, extract_info_dict

# json 파일로 압축하기
def process_json():
    raw_playlist =  get_playlist()[0] # 사용자가 선택한 playlist
    transformed_playlist = get_playlist()[1] # 해당 플레이리스트 내 곡들의 정제된 정보
    
    file_path_info = '/opt/airflow/data/raw_playlist.json' # 플레이리스트 내 곡 정보 >Docker 내 playlist_info.json으로 저장

    with open(file_path_info, 'w') as f:
        json.dump(raw_playlist, f, indent=2)
    
    return transformed_playlist

def query_playlist_tracks():
    query = f"INSERT INTO wired-epsilon-409307.OfflineStore.playlist_tracks VALUES "
    playlists = get_playlist()[1]
    for key, value in playlists.items():
        for i in range(len(value)):
            user_id = playlists[key][i]['user_id']
            playlist_id = playlists[key][i]['playlist_id']
            track_id = playlists[key][i]['track_id']
            timestamp = playlists[key][i]['timestamp']
            ratings = playlists[key][i]['ratings']
            
            query += f"('{playlist_id}', '{user_id}', '{track_id}',  {timestamp}, {ratings}),"
            
    query = query[:-1]    
    query += ";"
    return query
    

def query_playlist_track_dictionary():
    query = f"INSERT INTO wired-epsilon-409307.OfflineStore.playlist_track_dictionary VALUES "
    playlists = get_playlist()[1]
    for key, value in playlists.items():
        for i in range(len(value)):
            track_id = playlists[key][i]['track_id']
            title = playlists[key][i]['title'].replace("'", "\\'")  

            query += f"('{track_id}', '{title}'),"

    query = query[:-1]
    query += ";"
    return query

# S3 버킷으로 업로드
def _upload_playlist(filename: str, key: str, bucket_name: str) -> None:
    hook = S3Hook('aws_default')
    hook.load_file(filename=filename, key=key, bucket_name=bucket_name, replace=True)


# Airflow DAG 작성
with DAG("Logic_dag", start_date=datetime(2023, 8, 1),
         schedule_interval="@weekly", catchup=False) as dag:

    load_playlists = PythonOperator(
        task_id="load_playlists",
        python_callable=get_playlist
    )

    extract_playlist_info = PythonOperator(
        task_id="extract_playlist_info",
        python_callable=get_playlist
    )

    process_playlist = PythonOperator(
          task_id = "save_playlist",
          python_callable=process_json
    )

    upload_playlist_info = PythonOperator(
        task_id="upload_info_to_s3",
        python_callable=_upload_playlist,
        op_kwargs={
             "filename" : "/opt/airflow/data/raw_playlist.json",
             "key" : "/data/playlist.json",
             "bucket_name" : "spotifyproject123"
        }
    )

    truncate_playlist_tracks = BigQueryInsertJobOperator(
        task_id="truncate_playlist_tracks",
        configuration={
            "query" : {
                "query" : "TRUNCATE TABLE wired-epsilon-409307.OfflineStore.playlist_tracks;",
                "useLegacySql" : False,
                "priority" : "BATCH"}
            },
        location = bigquery_location
        )
    
    truncate_playlist_track_dictionary = BigQueryInsertJobOperator(
        task_id="truncate_playlist_track_dictionary",
        configuration={
            "query" : {
                "query" : "TRUNCATE TABLE wired-epsilon-409307.OfflineStore.playlist_track_dictionary;",
                "useLegacySql" : False,
                "priority" : "BATCH"}
            },
        location = bigquery_location
        )

    insert_bigquery_playlist_tracks = BigQueryInsertJobOperator(
        task_id="insert_playlist_tracks",
        configuration={
            "query" : {
                "query" : query_playlist_tracks(),
                "useLegacySql" : False,
                "priority" : "BATCH"}
            },
        location = bigquery_location
        )
    
    insert_bigquery_playlist_track_dictionary = BigQueryInsertJobOperator(
        task_id="insert_playlist_track_dictionary",
        configuration={
            "query" : {
                "query" : query_playlist_track_dictionary(),
                "useLegacySql" : False,
                "priority" : "BATCH"}
            },
        location = bigquery_location
        )

    load_playlists >> extract_playlist_info >> process_playlist >> upload_playlist_info >> truncate_playlist_tracks >> truncate_playlist_track_dictionary >> [insert_bigquery_playlist_tracks, insert_bigquery_playlist_track_dictionary]