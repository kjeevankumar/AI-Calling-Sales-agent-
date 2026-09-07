import os
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../files/backend/.env"))

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
SERVER_URL = os.getenv("SERVER_URL")

# Target test phone number
target_phone = "+917816006648"

print(f"Attempting to call: {target_phone}")
print(f"From Twilio Number: {TWILIO_PHONE_NUMBER}")

url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Calls.json"
auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
payload = {
    "To"            : target_phone,
    "From"          : TWILIO_PHONE_NUMBER,
    "Url"           : f"{SERVER_URL}/api/call/twiml",
}

try:
    resp = httpx.post(url, data=payload, auth=auth)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 201:
        print("✅ Call Placed Successfully!")
        print(f"Call Details: {resp.text}")
    else:
        print("❌ Twilio Call Failed!")
        print(f"Response: {resp.text}")
except Exception as e:
    print(f"❌ Connection error: {e}")
