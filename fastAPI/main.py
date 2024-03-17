from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from google.cloud import pubsub_v1
from datetime import datetime
import json, os
import logging

# 환경 설정
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'GCP_CREDENTIAL_KEY.json'
USER_ID = 'SPOTIFY_CLIENT_ID'
SECRET = 'SPOTIFY_CLIENT_SECRET'
scope = ["user-library-read","user-read-recently-played"]

# Pub/Sub 클라이언트 설정
publisher = pubsub_v1.PublisherClient()
topic_name_playlist = 'projects/{project_id}/topics/{topic}'.format(project_id='GCP_PROJECT_NAME', topic='userplaylist_tracks')
topic_userplaylistinfo = 'projects/{project_id}/topics/{topic}'.format(project_id='GCP_PROJECT_NAME', topic='userplaylistinfo')


# Spotify 데이터 가져오기 및 pub/sub 메시지 발행
def fetch_and_publish_spotify_data(sp, user_id, playlist_id):
    

    user_playlist = sp.playlist_tracks(playlist_id)

    for item in user_playlist['items']:
        track_id = item['track']['id']
        track_name = item['track']['name']
        track_popularity = float(item['track']['popularity'])
        track_timestamp = datetime.fromisoformat(item['added_at'].rstrip("Z")).timestamp()

        playlist_track = {
            "user_id": user_id,
            "playlist_id" : playlist_id,
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

        except Exception as e:
            print(f"An error occurred: {e}")
            

# Spotify 데이터 가져오기 및 pub/sub 메시지 발행
def fetch_and_publish_userplaylist_data(user_id, playlist_id):

    # JSON으로 변환하고 utf-8로 인코딩하여 메시지 발행
    user_playlist_json = json.dumps({'user_id':user_id, 'playlist_id':playlist_id})

    future_playlistinfo = publisher.publish(topic_userplaylistinfo, data=user_playlist_json.encode('utf-8'))
    
    try:
        # 결과 확인
        p_message_id = future_playlistinfo.result()
        print(f"User_playlist_info Message ID: {p_message_id}")

    except Exception as e:
        print(f"An error occurred: {e}")
            

''' API 호출을 위한 pydantic model 정의'''
class UserIdInfo(BaseModel):
    user_id: str


class UserPlaylistInfo(BaseModel):
    user_id : str
    playlist_id : str            


#fastapi app 선언 
app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.post("/get_playlists")
async def get_spotify_playlists(userinfo: UserIdInfo):
    """
    사용자가 입력한 user_id를 기반으로 해당 사용자의 플레이리스트 목록을 가져오는 api 입니다.

    입력 인자 : form에 입력한 user_id
    """
    # Spotify 설정
    auth_manager=SpotifyClientCredentials(client_id=USER_ID, client_secret=SECRET)
    logging.info(spotipy.Spotify(client_credentials_manager=auth_manager))
    sp = spotipy.Spotify(client_credentials_manager=auth_manager)
   
    show_playlists = []
    playlists = sp.user_playlists(userinfo.user_id)
    for playlist in playlists['items']:
        playlist_name = playlist['name']
        playlist_id = playlist['id']
        data = {'playlist' : playlist_name, 'playlist_id' : playlist_id}
        show_playlists.append(data)
    return show_playlists




@app.post("/user_playlist_info")
async def add_userplaylist_info(userinfo:UserPlaylistInfo):
    '''
    사용자 플레이리스트 기반 추천에 필요한 user_id, playlist_id를
    Bigquery Online.userplaylistinfo 테이블에 user_id, playlist_id 적재하는 api
    
    입력 인자 : user_id(str), playlist_id(str)
    '''
    
    #bigquery에 user_playlist_info 적재
    fetch_and_publish_userplaylist_data(userinfo.user_id, userinfo.playlist_id)
    
    user_data = {
        'user_id': userinfo.user_id,
        'playlist_id': userinfo.playlist_id
    }  
    
    return json.dumps(user_data)

    


@app.post("/playlist_recommendation")
async def get_playlist_recommend(userinfo:UserPlaylistInfo):
    '''
    사용자 플레이리스트 기반 추천 플레이리스트 track들의 track_id, title을 제공하는 api
    
    입력 인자 : user_id(str), playlist_id(str)
    '''
    
    # Spotify 설정
    auth_manager=SpotifyClientCredentials(client_id=USER_ID, client_secret=SECRET)
    sp = spotipy.Spotify(client_credentials_manager=auth_manager)
    # pub/sub으로 OnlineFeatureStore에 데이터 적재하기 
    fetch_and_publish_spotify_data(sp, userinfo.user_id, userinfo.playlist_id)
    
    url = 'https://bert4rec-inference-jjj2x6djpq-du.a.run.app/playlist_rec'  
    
    user_data = {
        'user_id': userinfo.user_id,
        'playlist_id': userinfo.playlist_id
    }  

    rec_result = requests.post(url, json=user_data).json()
    artist_name = []

    for track_id in rec_result['recommendations']['track_id']:
        artist_name.append(sp.track(track_id)['artists'][0]['name'])
        
    result = {
        'track_id': rec_result['recommendations']['track_id'],
        'track_title': rec_result['recommendations']['track_title'],
        'track_artist': artist_name,
    } 

    return result
    
    
@app.get("/artist_search/")
async def get_artist_genre(artist: str):
    '''
    아티스트 이름(str)를 입력하면 해당 아티스트의 장르를 반환하는 api
    
    입력 인자 : artist(str)
    '''
    
    auth_manager=SpotifyClientCredentials(client_id=USER_ID, client_secret=SECRET)
    sp = spotipy.Spotify(client_credentials_manager=auth_manager)
    result = sp.search(q=f"{artist}", limit=1, type="artist")
    try:
        genre = result['artists']['items'][0]['genres']
        if genre == []:
              genre.append("no genre result")
    except:
          genre = "no genre result"
    
    return {'artist_genre': genre}



@app.get("/track_search/")
async def get_track_id(track_title: str):
    '''
    track_title(str)를 입력하면 해당 트랙의 track_id를 반환하는 api
    
    입력 인자 : track_title(str)
    '''
    auth_manager=SpotifyClientCredentials(client_id=USER_ID, client_secret=SECRET)
    sp = spotipy.Spotify(client_credentials_manager=auth_manager)
    track_result = sp.search(q=f"{track_title}", limit=1, type="track")
    try:
        track_id = track_result["tracks"]["items"][0]["id"]

    except:
        track_id = "no track result"

    return {'track_id': track_id}

# "/rec_track"로 접근하면 rec_artist, rec_track, rec_uri를 리턴
@app.get("/rec_track/")
async def get_rec_track(track_id: str):
    '''
    track_id(str)를 입력하면 해당 트랙와 유사한 트랙의
    rec_artist(아티스트 이름), rec_track(트랙 이름), rec_uri(uri 정보)를 반환하는 api
    
    입력 인자 : track_id(str)
    '''
 
    try:
        auth_manager=SpotifyClientCredentials(client_id=USER_ID, client_secret=SECRET)
        sp = spotipy.Spotify(client_credentials_manager=auth_manager)
        rec_result = sp.recommendations(type='track', seed_tracks=[track_id], limit=1) # limit 1
        rec_artist = rec_result['tracks'][0]['artists'][0]['name']
        rec_track = rec_result["tracks"][0]["name"]
        rec_uri = rec_result["tracks"][0]["uri"]


  
        rec_feature_info = await get_track_features(rec_uri)


        rec_info = {
                    "rec_artist": rec_artist,
                    "rec_track": rec_track,
                    "rec_uri": rec_uri
                    }
        


    except:
        rec_info = "no rec_track result"
    
    return rec_info

@app.get("/track_features/")
async def get_track_features(rec_track_uri: str):
    '''
    rec_track_uri(str)를 입력하면 해당 트랙의
    danceability, instrumentalness, speechness, tempo, valence를 반환하는 api
    
    입력 인자 : rec_track_uri(str)
    '''

    try:
        auth_manager=SpotifyClientCredentials(client_id=USER_ID, client_secret=SECRET)
        sp = spotipy.Spotify(client_credentials_manager=auth_manager)
        
        features = sp.audio_features(tracks=[rec_track_uri])
        
        danceability = features[0]["danceability"]
        instrumentalness = features[0]["instrumentalness"]
        speechiness = features[0]["speechiness"]
        tempo = features[0]["tempo"]
        valence = features[0]["valence"]

        rec_feature_info = {
                    "danceability" : danceability,
                    "instrumentalness" : instrumentalness,
                    "speechiness" : speechiness,
                    "tempo" : tempo,
                    "valence" : valence
                }
        
    except:
        rec_feature_info = "no recommendation result"

    return rec_feature_info




# 서버 실행
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080) 
