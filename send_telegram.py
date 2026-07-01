import requests
import os

from dotenv import load_dotenv

load_dotenv()       #loads .env data

TOKEN = os.getenv("TELEGRAM_TOKEN")     #Telegram bot token
CHAT_ID = os.getenv("CHAT_ID")

def send_message(text):
    """
    Sends message to telegram bot.

    :param text: message to send
    :return: true if success in sending, false otherwise
    """

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "parse_mode": "Markdown",
        "text": text
    }

    try:
        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            return True
        else:
            return False

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return False

if __name__ == '__main__':

    message = "pene"

    send_message(message)