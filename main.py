import network
import socket
import time
import urequests
import ujson
import gc
from machine import Pin

# Wi-Fi Configuration
SSID = 'WIFI_SSID'
PASSWORD = 'PASSWORD'

# Telegram Bot Configuration
BOT_TOKEN = 'TELEGRAM_BOT_TOKEN'
LAST_UPDATE_ID = 0

# PC Configuration
PC_MAC = 'A036BCBD082B'  # Format: AABBCCDDEEFF or AA:BB:CC:DD:EE:FF
BROADCAST_ADDR = '255.255.255.255'
WOL_PORT = 9

led = Pin("LED", Pin.OUT)

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    retries = 0
    while not wlan.isconnected() and retries < 20:
        print('Connecting to Wi-Fi...')
        time.sleep(1)
        retries += 1
    if wlan.isconnected():
        print('Connected:', wlan.ifconfig())
    else:
        print('Failed to connect after retries.')
    return wlan

def ensure_wifi(wlan):
    if not wlan.isconnected():
        print("Wi-Fi disconnected. Attempting reconnection...")
        wlan.disconnect()
        wlan.connect(SSID, PASSWORD)
        retries = 0
        while not wlan.isconnected() and retries < 10:
            print("Reconnecting...")
            time.sleep(1)
            retries += 1
        if wlan.isconnected():
            print("Reconnected:", wlan.ifconfig())
        else:
            print("Reconnection failed.")

def clean_mac(mac):
    return mac.replace(':', '').replace('-', '')

def create_magic_packet(mac):
    mac = clean_mac(mac)
    mac_bytes = bytes.fromhex(mac)
    return b'\xff' * 6 + mac_bytes * 16

def send_wol():
    try:
        wol_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        wol_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        wol_socket.sendto(create_magic_packet(PC_MAC), (BROADCAST_ADDR, WOL_PORT))
        wol_socket.close()
        print("WoL packet sent.")
    except Exception as e:
        print("WoL error:", e)

def send_telegram_message(chat_id, text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    data = {'chat_id': chat_id, 'text': text}
    try:
        response = urequests.post(url, json=data)
        response.close()
    except Exception as e:
        print('Telegram send error:', e)

def check_telegram():
    global LAST_UPDATE_ID
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={LAST_UPDATE_ID + 1}&timeout=25'
    try:
        response = urequests.get(url)
        data = ujson.loads(response.text)
        response.close()
        if data['ok'] and len(data['result']) > 0:
            for update in data['result']:
                LAST_UPDATE_ID = update['update_id']
                msg = update.get('message', {})
                chat_id = msg.get('chat', {}).get('id')
                text = msg.get('text', '').strip().lower()

                if not chat_id or not text:
                    continue

                print("Received:", text)

                if text == '/start':
                    send_telegram_message(chat_id, "Raspberry Pi Pico W is running!")

                elif text == '/poweron':
                    send_wol()
                    send_telegram_message(chat_id, "WoL magic packet sent! PC on.")
                    led.value(True)
                    time.sleep(2)
                    led.value(False)

                else:
                    print('Error command')
                    #send_telegram_message(chat_id, "Unknown command.")

    except Exception as e:
        print('Telegram check error:', e)

def main():
    wlan = connect_wifi()
    led.value(True)
    time.sleep(2)
    led.value(False)
    print("Bot started. Listening for commands...")

    while True:
        ensure_wifi(wlan)
        check_telegram()
        gc.collect()
        time.sleep(5)

if __name__ == '__main__':
    main()
