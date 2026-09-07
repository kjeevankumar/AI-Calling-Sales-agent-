import httpx
try:
    print("Testing connection to tunnel...")
    resp = httpx.get("https://828f73ef3bc6ef.lhr.life/api/leads", timeout=10)
    print("Status code:", resp.status_code)
    print("Content:", resp.text[:100])
except Exception as e:
    print("Error:", e)
