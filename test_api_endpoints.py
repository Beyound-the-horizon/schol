from fastapi.testclient import TestClient
from ai.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["api_version"] == "v1"
    print("[Test Health] Passed:", data)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "docs_url" in data
    print("[Test Root] Passed:", data)

def test_scholarships_list():
    response = client.get("/api/v1/scholarships?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "scholarships" in data
    assert "count" in data
    print(f"[Test Scholarships List] Passed: Found {data['count']} scholarships in DB")

if __name__ == "__main__":
    test_health()
    test_root()
    test_scholarships_list()
    print("[ALL API TESTS PASSED SUCCESSFULLY!]")

