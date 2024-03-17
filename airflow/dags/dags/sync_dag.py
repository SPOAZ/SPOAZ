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

bigquery_location = "asia-northeast3"

def load_tracks_from_onlinestore(**kwargs):
    project_id = "wired-epsilon-409307"
    
    bigquery_hook = BigQueryHook(
        bigquery_conn_id = "google_cloud_default",
        use_legacy_sql = True,
        location="asia-northeast3",
        priority="INTERACTIVE"
    )

    sql = "SELECT * FROM OnlineStore.playlist_tracks"
    
    connection = bigquery_hook.get_conn()
    cursor = connection.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()

    df = [row for row in rows] # [[user_id, playlist_id]] 획득?
    return df

def load_dictionary_from_onlinestore(**kwargs):
    project_id = "wired-epsilon-409307"
    
    bigquery_hook = BigQueryHook(
        bigquery_conn_id = "google_cloud_default",
        use_legacy_sql = True,
        location="asia-northeast3",
        priority="INTERACTIVE"
    )

    sql = "SELECT * FROM OnlineStore.playlist_track_dictionary"
    
    connection = bigquery_hook.get_conn()
    cursor = connection.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()

    df = [row for row in rows] # [[user_id, playlist_id]] 획득?
    return df


# 일주일 단위로 기존 플레이리스트의 곡 가져오기
def get_playlist_dictionary(): # user_id, playlist_id
    dictionary = load_dictionary_from_onlinestore() # dataframe 획득

    playlist_dictionary = []
    

    for info in dictionary:
        extract_info_dict = {}
        extract_info_dict['track_id'] = info[0]
        extract_info_dict['title'] = info[1]
        playlist_dictionary.append(extract_info_dict)

    return playlist_dictionary


def get_playlist_tracks(): # user_id, playlist_id
    user_data = load_tracks_from_onlinestore() # dataframe 획득

    playlist_tracks = []
    
    for info in user_data:
        playlist_dict = {}
        playlist_dict['user_id'] = info[0]
        playlist_dict['playlist_id'] = info[1]
        playlist_dict['track_id'] = info[2]
        playlist_dict['timestamp'] = info[3]
        playlist_dict['ratings'] = info[4]

        playlist_tracks.append(playlist_dict)

    return playlist_tracks


def query_playlist_tracks():
    query = f"""MERGE INTO OfflineStore.playlist_tracks AS target
USING
  OnlineStore.playlist_tracks AS source
ON target.user_id = source.user_id AND target.playlist_id = source.playlist_id AND target.track_id = source.track_id
WHEN NOT MATCHED THEN
  INSERT (user_id, playlist_id, track_id, timestamp, ratings)
  VALUES (source.user_id, source.playlist_id, source.track_id, source.timestamp, source.ratings)"""    
    return query
    

def query_playlist_track_dictionary():
    query = f"""MERGE INTO OfflineStore.playlist_track_dictionary AS target
USING 
  OnlineStore.playlist_track_dictionary
AS source
ON target.track_id = source.track_id AND target.title = source.title
WHEN NOT MATCHED THEN
  INSERT (track_id, title)
  VALUES (source.track_id, source.title)
"""
    return query


# Airflow DAG 작성
with DAG("Sync_dag", start_date=datetime(2023, 8, 1),
         schedule_interval="@daily", catchup=False) as dag:

    load_tracks_ = PythonOperator(
        task_id="load_tracks_from_onlinestore",
        python_callable=load_tracks_from_onlinestore
    )

    load_dictionary_ = PythonOperator(
        task_id="load_dictionary_from_onlinestore",
        python_callable=load_dictionary_from_onlinestore
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

    [load_tracks_, load_dictionary_] >> insert_bigquery_playlist_track_dictionary >> insert_bigquery_playlist_tracks