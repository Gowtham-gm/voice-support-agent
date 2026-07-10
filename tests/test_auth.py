def test_register_login_me(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "a@example.com", "password": "Passw0rd1", "full_name": "A B"},
    )
    assert r.status_code == 201

    r = client.post(
        "/api/v1/auth/login", json={"email": "a@example.com", "password": "Passw0rd1"}
    )
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@example.com"


def test_weak_password_rejected(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "b@example.com", "password": "weakpass", "full_name": "B"},
    )
    assert r.status_code == 422
