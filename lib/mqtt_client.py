import network
import socket
import struct
import time
import ssl

class MQTTClient:
    def __init__(self, client_id, server, port=8883, user=None, password=None, keepalive=0):
        self.client_id = client_id
        self.server = server
        self.port = port
        self.user = user
        self.password = password
        self.keepalive = keepalive
        self.sock = None
        self.connected = False
        
    def _check_conn(self):
        if not self.connected:
            raise OSError('Not connected')
            
    def connect(self):
        try:
            print("DNSルックアップ中...")
            ai = socket.getaddrinfo(self.server, self.port)[0]
            print(f"サーバーアドレス情報: {ai}")
            
            print("ソケット作成中...")
            self.sock = socket.socket(ai[0], ai[1], ai[2])
            self.sock.settimeout(10.0)
            
            print("SSL/TLS処理開始...")
            try:
                # Pico W用のSSL/TLS設定
                self.sock = ssl.wrap_socket(self.sock, do_handshake=True)
            except Exception as ssl_err:
                print(f"SSL初期化エラー: {ssl_err}")
                raise
            
            print(f"サーバー {ai[-1]} に接続中...")
            self.sock.connect(ai[-1])
            print("TCP接続確立")
            
            print("MQTT CONNECT送信中...")
            # 固定ヘッダ
            pkt = bytearray(b"\x10\x00")
            
            # 可変ヘッダ - プロトコル名と接続フラグ
            var_header = bytearray()
            var_header.extend(b"\x00\x04MQTT\x04")  # プロトコル名とバージョン
            
            # 接続フラグの設定
            connect_flags = 0
            if self.user is not None:
                connect_flags |= 0x80
            if self.password is not None:
                connect_flags |= 0x40
            var_header.append(connect_flags)
            
            # キープアライブ
            var_header.extend(struct.pack("!H", self.keepalive))
            
            # ペイロード
            payload = bytearray()
            # クライアントID
            payload.extend(struct.pack("!H", len(self.client_id)))
            payload.extend(self.client_id.encode())
            
            # ユーザー名とパスワード（設定されている場合）
            if self.user is not None:
                payload.extend(struct.pack("!H", len(self.user)))
                payload.extend(self.user.encode())
            if self.password is not None:
                payload.extend(struct.pack("!H", len(self.password)))
                payload.extend(self.password.encode())
            
            # パケット長の設定
            remaining_length = len(var_header) + len(payload)
            pkt[1] = remaining_length
            
            # パケット送信
            print(f"送信パケットサイズ: {len(pkt) + len(var_header) + len(payload)} bytes")
            self.sock.write(pkt)
            self.sock.write(var_header)
            self.sock.write(payload)
            
            print("CONNACK待機中...")
            resp = self.sock.read(4)
            print(f"受信したCONNACK: {resp}")
            
            if not resp:
                raise OSError("No CONNACK received")
            if resp[0] != 0x20 or resp[3] != 0:
                raise OSError(f"Connection refused: {resp[3]}")
            
            print("MQTT接続完了!")
            self.connected = True
            
        except Exception as e:
            print(f"接続エラー: {e}")
            if self.sock:
                self.sock.close()
            raise
            
    def disconnect(self):
        if self.connected:
            try:
                self.sock.write(b"\xe0\x00")
                self.sock.close()
            except Exception as e:
                print(f"切断エラー: {e}")
            finally:
                self.connected = False
        
    def publish(self, topic, msg, retain=False, qos=0):
        self._check_conn()
        try:
            pkt = bytearray(b"\x30\x00")
            pkt[0] |= qos << 1 | retain
            
            payload = bytearray()
            payload.extend(struct.pack("!H", len(topic)))
            payload.extend(topic.encode())
            
            if qos > 0:
                payload.extend(struct.pack("!H", 0))
                
            payload.extend(msg.encode())
            
            pkt[1] = len(payload)
            self.sock.write(pkt)
            self.sock.write(payload)
            print(f"メッセージを送信しました: {topic} -> {msg}")
            
        except Exception as e:
            print(f"送信エラー: {e}")
            raise