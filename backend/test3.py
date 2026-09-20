from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
response = client.post("/api/v1/events/dcb5abd0-2ae0-45bb-aded-86bd5fc4023f/override_plate", json={"plate_text": "TEST1234"})
print(response.status_code)
print(response.json() if response.status_code != 500 else response.text)
