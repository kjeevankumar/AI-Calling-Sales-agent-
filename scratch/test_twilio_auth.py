import os
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../files/backend/.env"))

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

print(f"Checking Twilio Credentials:")
print(f"Account SID: {TWILIO_ACCOUNT_SID}")
print(f"Phone Number: {TWILIO_PHONE_NUMBER}")

if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
    print("❌ Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN in .env")
    exit(1)

url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}.json"
auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

try:
    resp = httpx.get(url, auth=auth)
    if resp.status_code == 200:
        print("✅ Twilio Authentication Successful!")
        data = resp.json()
        print(f"Account Status: {data.get('status')}")
        print(f"Account Type: {data.get('type')}")
    else:
        print(f"❌ Twilio Authentication Failed with status code: {resp.status_code}")
        print(f"Response: {resp.text}")
except Exception as e:
    print(f"❌ Error connecting to Twilio: {e}")
