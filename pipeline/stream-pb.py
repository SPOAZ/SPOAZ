import spotipy
from spotipy.oauth2 import SpotifyOAuth
from google.cloud import pubsub_v1
from datetime import datetime
import json, os

# 환경 설정
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'GCP_CREDENTIAL_KEY.json'
USER_ID = 'YOUR_SPOTIFY_CLIENT_ID'
SECRET = "YOUR_SPOTIFY_CLIENT_SECRET"
scope = ["user-library-read","user-read-recently-played"]

# Spotify 설정
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=USER_ID, client_secret=SECRET, redirect_uri="http://127.0.0.1:8080", scope=scope))

# Pub/Sub 설정
publisher = pubsub_v1.PublisherClient()
topic_name_playlist = 'projects/{project_id}/topics/{topic}'.format(project_id='wired-epsilon-409307', topic='userplaylist_tracks')

# Spotify 데이터 가져오기 및 메시지 발행
def fetch_and_publish_spotify_data(sp):
    user_id = sp.current_user()['id']
    p_id = 'playlist_id'
    user_playlist = sp.playlist_tracks(p_id)

    for item in user_playlist['items']:
        track_id = item['track']['id']
        track_name = item['track']['name']
        #track_artist = item['track']['artists'][0]['name']
        #track_rdate = item['track']['album']['release_date']
        track_popularity = float(item['track']['popularity'])
        track_timestamp = datetime.fromisoformat(item['added_at'].rstrip("Z")).timestamp()

        playlist_track = {
            "user_id": user_id,
            "playlist_id" : p_id,
            "track_id": track_id,
            "title": track_name,
            "timestamp": track_timestamp,
            "ratings": track_popularity
        }
  
        
        # JSON으로 변환하고 utf-8로 인코딩하여 메시지 발행
        playlist_json = json.dumps(playlist_track)

        future_playlist = publisher.publish(topic_name_playlist, data=playlist_json.encode('utf-8'))
        
        try:
            # 결과 확인
            p_message_id = future_playlist.result()
            print(f"Playlist_tracks Message ID: {p_message_id}")
            print(playlist_json)

        except Exception as e:
            print(f"An error occurred: {e}")
            


# 메시지 발행 실행
fetch_and_publish_spotify_data(sp)
