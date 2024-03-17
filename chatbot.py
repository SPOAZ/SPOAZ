import openai
import streamlit as st
import requests
import json
import re

def get_track_rec(artist, track):
        '''Track 기반 추천 진행 함수'''

        genre_json= requests.get('http://127.0.0.1:8080/artist_search/', params={"artist": artist}).json()
        artist_genre = genre_json.get("artist_genre")

        track_json = requests.get('http://127.0.0.1:8080/track_search/', params={"track_title": track}).json()
        track_id = track_json.get("track_id","Track ID not found")
        
      
        sp_rec= requests.get('http://127.0.0.1:8080/rec_track/', params={"track_id": track_id}).json()
        rec_uri = sp_rec.get('rec_uri')
        features = requests.get('http://127.0.0.1:8080/track_features/', params={"rec_track_uri": rec_uri}).json()
        

        rec_artist, rec_track = sp_rec.get('rec_artist'), sp_rec.get('rec_track')

        result = f'{artist}의 "{track}": 해당 아티스트의 장르는 {", ".join(artist_genre)}입니다.\n'
        result += f' 추천드린 "{rec_artist}"의 "{rec_track}"은 다음과 같은 음악적 특성에 따라 해당곡과 유사하다고 보여집니다:\n'
        result += f'- 댄스성(danceability): {features["danceability"]}\n'
        result += f'- 악기 사용도(instrumentalness): {features["instrumentalness"]}\n'
        result += f'- 말하기 비율(speechiness): {features["speechiness"]}\n'
        result += f'- 템포(tempo): {features["tempo"]} BPM\n'
        result += f'- 긍정도(valence): {features["valence"]}'
        
        return result
    
def get_userplaylists(user_id):
    '''사용자 Spotify playlist 목록 반환하는 함수'''
    user_playlists = requests.post('http://127.0.0.1:8080/get_playlists/', json={"user_id": user_id}).json()
    
    playlist_titles={item['playlist']: item['playlist_id'] for item in user_playlists}
            
    return playlist_titles

def get_userplaylist_rec(user_id, playlist_id):
    '''사용자 플레이리스트 기반 추천 반환하는 함수 '''
    #사용자 user_id, playlist_id bigquery Onlinestore.userplaylistinfo에 적재
    requests.post('http://127.0.0.1:8080/user_playlist_info/', json={"user_id": user_id, "playlist_id": playlist_id}).json()
    #
    playlist_rec= requests.post('http://127.0.0.1:8080/playlist_recommendation/', json={"user_id": user_id, "playlist_id": playlist_id}).json()
    
    result='해당 플레이리스트 기반 음악 추천 결과는 다음과 같습니다.\n'
    for i in range(len(playlist_rec['track_id'])):
            artist = playlist_rec["track_artist"][i]
            title = playlist_rec["track_title"][i]
            result += f'{i+1}. {artist} - "{title}"\n'
    
    return result
    

#### openai chatbot 함수 정의
track_rec = [
    # get_track_rec 함수에 대한 메타데이터
    {
        "type": "function",
        "name": "get_track_rec",
        "description": "Explain the track's information from a given recommended artist, track, artist's genre and track's features",
        "parameters": {
            "type": "object",
            "properties": {
                "artist": {"type": "string", "description": "The artist, e.g. BTS"},
                "track": {"type": "string", "description": "The track, e.g. Dynamite"}
            },
            "required": ["artist", "track"],
        },
    }]

playlist_rec = [# get_userplaylists 함수에 대한 메타데이터
    {
        "type": "function",
        "name": "get_userplaylists",
        "description": "Get user's Spotify playlists based on user ID",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
            },
            "required": ["user_id"],
        },
    },
    # get_userplaylist_rec 함수에 대한 메타데이터
    {
        "type": "function",
        "name": "get_userplaylist_rec",
        "description": "Get recommendation based of user's Spotify playlists",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "playlist_id": {"type": "string"}
            },
            "required": ["user_id", "playlist_id"],
        },
    },
]    

def check_artist_and_track(message):
    # 정규 표현식을 사용하여 아티스트와 트랙 이름이 있는지 확인
    pattern = r"(?P<artist>.+?)의 (?P<track>.+?)[와과랑] 비슷한 노래 추천해줘"
    match = re.search(pattern, message)
    return bool(match)  

def run_conversation(messages):
    latest_message = messages[-1]["content"].lower()

    response_message = ''

    # 트랙기반 추천 요청
    if check_artist_and_track(latest_message):
        # 아티스트와 트랙 추출
        response = openai.ChatCompletion.create(
            model="CUSTOM_GPT_MODEL_ID", # 커스텀 GPT 모델 id
            messages=[{"role": "user", "content": latest_message}],
            functions=track_rec
        )
        response = json.loads(response["choices"][0]["message"]['function_call']['arguments'])

        artist, track = response['artist'], response['track']
        response_message = get_track_rec(artist, track)
        
    
    else:
        # GPT-3 모델을 호출하여 추천 받기
        response = openai.ChatCompletion.create(
            model="CUSTOM_GPT_MODEL_ID", # 커스텀 GPT 모델 id
            messages=[{"role": "user", "content": latest_message}]
        )
        response_message = response["choices"][0]["message"]['content']


     
    return response_message or "요청하신 내용을 처리할 수 없습니다. 다시 시도해주세요."
    
    


###### openai chatbot ######
with st.sidebar:
    # openai_api_key = " "
    openai_api_key = "OPENAI_API_KEY"
    "[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://github.com/SPOAZ/SPOAZ.git)"

st.title("💬 Chatbot")


"""
저희 기능에는 1. `트랙 기반 음악 추천` 2. `감성 기반 음악 추천` 3.  `사용자 플레이리스트 기반 추천` 기능이 있습니다. \n
[Spotify premium](https://www.spotify.com/kr-ko/premium/)을 체험해보시고 저희 기능을 사용해보세요! \n
⚠️ 무료 체험 기간이 지나면 과금이 됩니다. 
"""
st.caption("🚀 A streamlit chatbot powered by OpenAI LLM")

 
if 'spotify_user_id' not in st.session_state:
    st.session_state['spotify_user_id'] = ''
if 'user_playlists' not in st.session_state:
    st.session_state['user_playlists'] = {}
if 'selected_playlist_title' not in st.session_state:
    st.session_state['selected_playlist_title'] = None

# Spotify 사용자 ID 입력과 'Get Playlists' 버튼
st.session_state['spotify_user_id'] = st.text_input("사용자의 Spotify 고유 아이디를 입력 해주세요:")
if st.button('Get Playlists'):
    st.session_state['user_playlists'] = get_userplaylists(st.session_state['spotify_user_id'])
    if st.session_state['user_playlists']:
        # 사용자가 플레이리스트를 선택하면, 이 선택을 session_state에 저장합니다.
        playlist_titles = list(st.session_state['user_playlists'].keys())
        st.session_state['selected_playlist_title'] = st.selectbox("Select a playlist:", playlist_titles)
# 드롭다운에서 선택한 후 'Get Recommendations' 버튼
if st.session_state['selected_playlist_title']:
    playlist_title = st.session_state['selected_playlist_title']
    if st.button("Get Recommendations"):
        playlist_id = st.session_state['user_playlists'][playlist_title]
        response_message = get_userplaylist_rec(st.session_state['spotify_user_id'], playlist_id)
        st.write(response_message)
        
        # 결과를 받은 후 사용자 ID 입력 필드를 초기화
        st.session_state['spotify_user_id'] = ''  # 이렇게 하면 입력 필드가 초기화됩니다.
        # 선택된 플레이리스트 타이틀도 초기화
        st.session_state['selected_playlist_title'] = None
        # 사용자 플레이리스트 정보도 초기화
        st.session_state['user_playlists'] = {}


if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "어떤 음악을 듣고 싶으신가요?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])
       
# 일반 채팅을 사용해 추천 받는 경우
if prompt := st.chat_input():
    if not openai_api_key:
        st.info("Please add your OpenAI API key to continue.")
        st.stop()
        
    else:
        openai.api_key = openai_api_key
        # 사용자 메시지를 대화 내역에 추가
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        messages = st.session_state.messages
            
        response = run_conversation(messages)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.write(response)
