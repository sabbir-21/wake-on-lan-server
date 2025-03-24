import network
import socket
import time
import urequests
import ujson
from machine import Pin

# Wi-Fi Configuration
SSID = 'wifi_ssid'
PASSWORD = 'password'

# Telegram Bot Configuration
BOT_TOKEN = 'Telegram_BOT_TOKEN'
LAST_UPDATE_ID = 0

# PC Configuration
PC_MAC = 'A036BCBD082B'
BROADCAST_ADDR = '255.255.255.255'
WOL_PORT = 9

led = Pin("LED", Pin.OUT)

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    while not wlan.isconnected():
        print('Connecting...')
        time.sleep(1)
    print('Connected:', wlan.ifconfig())
    return wlan

def create_magic_packet(mac):
    mac_bytes = bytes.fromhex(mac)
    return b'\xff' * 6 + mac_bytes * 16

def send_wol():
    wol_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    wol_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    wol_socket.sendto(create_magic_packet(PC_MAC), (BROADCAST_ADDR, WOL_PORT))
    wol_socket.close()
    
def send_telegram_message(chat_id, text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    data = {'chat_id': chat_id, 'text': text}
    try:
        response = urequests.post(url, json=data)
        response.close()
    except Exception as e:
        print('Message send error:', e)

def check_telegram():
    global LAST_UPDATE_ID
    #url = f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={LAST_UPDATE_ID + 1}'
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={LAST_UPDATE_ID + 1}&timeout=25'

    
    try:
        response = urequests.get(url)
        '''
        if response.status_code == 429:
            print("Rate limited! Waiting 10s...")
            time.sleep(10)
            return
        '''
        data = ujson.loads(response.text)
        response.close()
        
        if data['ok'] and len(data['result']) > 0:
            for update in data['result']:
                LAST_UPDATE_ID = update['update_id']
                msg = update['message']
                chat_id = msg['chat']['id']
                text = msg['text'].strip().lower()
                
                parts = text.split()
                if not parts:
                    continue
                
                command = parts[0]
                
                if command == '/start':
                    print("start message")
                    send_telegram_message(chat_id, "Raspberry Pi Pico W is running!")
                
                elif command == '/poweron':
                    print("PC on")
                    send_wol()
                    send_telegram_message(chat_id, "WoL magic packet sent! PC on")
                    led.value(True)
                    time.sleep(2)
                    led.value(False)
                
                else:
                    print("error")
                    
    except Exception as e:
        print('Update error:', e)

def main():
    connect_wifi()
    print("Bot started. Waiting for commands...")
    led.value(True)
    time.sleep(2)
    led.value(False)
    while True:
        check_telegram()
        time.sleep(5)

if __name__ == '__main__':
    main()
