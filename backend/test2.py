import requests

url = "http://localhost:8000/api/v1/events/dcb5abd0-2ae0-45bb-aded-86bd5fc4023f/override_plate"
payload = {"plate_text": "TEST1234"}
try:
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(e)
