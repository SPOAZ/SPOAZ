"""
(Batch) 사용자가 선택한 플레이리스트 내 곡들의 정보를 저장하는 모듈 입니다.
"""

from datetime import datetime

class DataExtractor:

    def __init__(self, playlist):
        #self.playlists = PlayLists
        self.playlist = playlist
        
    def extract_track(self):
        tracks = self.playlist['tracks']

        playlist = []
        
        for track in tracks['items']:
            playlist_id = self.playlist['id']
            user_id = track['added_by']['id'] # User_id
            track_id = track['track']['id'] # track_id
            title = track['track']['name'] # title 
            artist = track['track']['album']['artists'][0]['name'] # Artist
            timestamp = datetime.fromisoformat(track['added_at'].rstrip("Z")).timestamp() # timestamp
            ratings = track['track']['popularity'] # ratings
            
            track_info = {'playlist_id' : playlist_id, 'user_id': user_id, 'track_id': track_id, 'title': title, 'artist': artist, 'timestamp': timestamp, 'ratings': ratings}

            playlist.append(track_info)

        return playlist



