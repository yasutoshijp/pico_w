def run():
    print("Running 02.send_to_ss.py...")
    # 必要な処理をここに追加
    print("Finished 02.send_to_ss.py!")
fba258f13899e421b3ab7a3a50488807

import requests

# ChatWork API トークン
API_TOKEN = 'fba258f13899e421b3ab7a3a50488807'  # ここにChatWorkのAPIトークンを入力

# 送信先ルームID（ChatWorkのルームIDを入力）
ROOM_ID = '67549413'

# 送信メッセージ
MESSAGE = 'PythonからChatWorkにメッセージを送信しています！'

# ChatWork API エンドポイント
API_ENDPOINT = f'https://api.chatwork.com/v2/rooms/{ROOM_ID}/messages'

# HTTPヘッダー
headers = {
    'X-ChatWorkToken': API_TOKEN
}

# メッセージ送信データ
data = {
    'body': MESSAGE
}

# POSTリクエストでメッセージを送信
response = requests.post(API_ENDPOINT, headers=headers, data=data)

# レスポンスの確認
if response.status_code == 200:
    print('PICO4号機からメッセージです。', response.json())
else:
    print('エラーが発生しました:', response.status_code, response.text)

# 実行
if __name__ == "__main__":
    run()
