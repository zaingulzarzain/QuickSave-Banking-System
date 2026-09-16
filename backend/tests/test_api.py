"""End-to-end API tests: auth, banking, transfers, admin, AI."""

import uuid


def _unique_email():
    return f"u{uuid.uuid4().hex[:8]}@example.com"


# ---------------------------------------------------------------- health/auth

def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_login_me(client):
    email = _unique_email()
    r = client.post("/api/v1/auth/register", json={
        "email": email, "full_name": "New User", "password": "secret123",
    })
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    assert token

    # New users get a welcome-bonus checking account
    accounts = client.get(
        "/api/v1/accounts", headers={"Authorization": f"Bearer {token}"}
    ).json()
    assert len(accounts) == 1
    assert accounts[0]["balance"] == 100.0

    r = client.post("/api/v1/auth/login", json={
        "email": email, "password": "secret123",
    })
    assert r.status_code == 200

    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.json()["email"] == email


def test_login_rejects_bad_password(client, user_factory):
    user = user_factory("login")
    r = client.post("/api/v1/auth/login", json={
        "email": user.email, "password": "wrong-password",
    })
    assert r.status_code == 401


def test_protected_routes_need_token(client):
    assert client.get("/api/v1/accounts").status_code == 401


# ------------------------------------------------------------------ banking

def _register(client):
    email = _unique_email()
    r = client.post("/api/v1/auth/register", json={
        "email": email, "full_name": "Bank User", "password": "secret123",
    })
    assert r.status_code == 201
    return r.json()["access_token"], r.json()["user"]


def test_open_account_deposit_withdraw(client):
    token, _ = _register(client)
    h = {"Authorization": f"Bearer {token}"}

    r = client.post("/api/v1/accounts", json={
        "account_type": "savings",
        "account_name": "Rainy Day",
        "initial_deposit": 500,
    }, headers=h)
    assert r.status_code == 201, r.text
    acc = r.json()
    assert acc["balance"] == 500.0
    assert acc["account_number"].startswith("QS")

    r = client.post(f"/api/v1/accounts/{acc['id']}/deposit", json={
        "amount": 250, "description": "Side gig payout",
    }, headers=h)
    assert r.status_code == 200
    assert r.json()["balance_after"] == 750.0

    r = client.post(f"/api/v1/accounts/{acc['id']}/withdraw", json={
        "amount": 50, "description": "ATM cash",
    }, headers=h)
    assert r.status_code == 200
    assert r.json()["balance_after"] == 700.0

    # History reflects all three entries
    r = client.get(f"/api/v1/accounts/{acc['id']}/transactions", headers=h)
    assert r.json()["total"] == 3


def test_withdraw_insufficient_funds(client):
    token, _ = _register(client)
    h = {"Authorization": f"Bearer {token}"}
    acc = client.get("/api/v1/accounts", headers=h).json()[0]
    r = client.post(f"/api/v1/accounts/{acc['id']}/withdraw", json={
        "amount": 999_999, "description": "too much",
    }, headers=h)
    assert r.status_code == 400


def test_transfer_is_atomic_and_balanced(client):
    token_a, _ = _register(client)
    token_b, _ = _register(client)
    ha, hb = {"Authorization": f"Bearer {token_a}"}, {"Authorization": f"Bearer {token_b}"}

    acc_a = client.get("/api/v1/accounts", headers=ha).json()[0]
    acc_b = client.get("/api/v1/accounts", headers=hb).json()[0]
    bal_a_before, bal_b_before = acc_a["balance"], acc_b["balance"]

    r = client.post("/api/v1/transactions/transfer", json={
        "from_account_id": acc_a["id"],
        "to_account_number": acc_b["account_number"],
        "amount": 40,
        "description": "Dinner split",
    }, headers=ha)
    assert r.status_code == 200, r.text
    assert r.json()["debit"]["type"] == "transfer_out"
    assert r.json()["credit"]["type"] == "transfer_in"

    acc_a_after = client.get(f"/api/v1/accounts/{acc_a['id']}", headers=ha).json()
    acc_b_after = client.get(f"/api/v1/accounts/{acc_b['id']}", headers=hb).json()
    assert acc_a_after["balance"] == round(bal_a_before - 40, 2)
    assert acc_b_after["balance"] == round(bal_b_before + 40, 2)


def test_transfer_to_self_rejected(client):
    token, _ = _register(client)
    h = {"Authorization": f"Bearer {token}"}
    acc = client.get("/api/v1/accounts", headers=h).json()[0]
    r = client.post("/api/v1/transactions/transfer", json={
        "from_account_id": acc["id"],
        "to_account_number": acc["account_number"],
        "amount": 10,
    }, headers=h)
    assert r.status_code == 400


def test_account_lookup(client):
    token_a, _ = _register(client)
    token_b, _ = _register(client)
    acc_b = client.get(
        "/api/v1/accounts", headers={"Authorization": f"Bearer {token_b}"}
    ).json()[0]
    r = client.get(
        f"/api/v1/accounts/lookup/{acc_b['account_number']}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert r.status_code == 200
    assert r.json()["owner_display"].startswith("Bank")


def test_users_cannot_see_each_others_accounts(client):
    token_a, _ = _register(client)
    token_b, _ = _register(client)
    acc_b = client.get(
        "/api/v1/accounts", headers={"Authorization": f"Bearer {token_b}"}
    ).json()[0]
    r = client.get(
        f"/api/v1/accounts/{acc_b['id']}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert r.status_code == 403


# ------------------------------------------------------------------- admin

def test_admin_stats_and_freeze(client, user_factory, auth_headers):
    admin = user_factory("admin", is_admin=True)
    plain = user_factory("plain")
    ha, hp = auth_headers(admin), auth_headers(plain)

    # Non-admins are locked out
    assert client.get("/api/v1/admin/stats", headers=hp).status_code == 403

    r = client.get("/api/v1/admin/stats", headers=ha)
    assert r.status_code == 200
    assert r.json()["total_users"] >= 2

    # Admin can freeze an account; frozen accounts block withdrawals
    acc = client.post("/api/v1/accounts", json={
        "account_type": "checking", "account_name": "Temp",
        "initial_deposit": 100,
    }, headers=hp).json()
    r = client.patch(f"/api/v1/admin/accounts/{acc['id']}/status",
                     json={"status": "frozen"}, headers=ha)
    assert r.json()["status"] == "frozen"
    r = client.post(f"/api/v1/accounts/{acc['id']}/withdraw",
                    json={"amount": 10}, headers=hp)
    assert r.status_code == 403


# ---------------------------------------------------------------------- AI

def test_ai_chat_fallback(client):
    token, _ = _register(client)
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/api/v1/ai/chat", json={"message": "What is my balance?"}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["provider"] in ("quicksave-local", "openai-compatible")
    assert "balance" in body["reply"].lower()
    assert body["suggestions"]


def test_ai_insights(client):
    token, _ = _register(client)
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/ai/insights?days=30", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["period_days"] == 30
    assert "narrative" in body and len(body["narrative"]) > 10
    assert isinstance(body["by_category"], list)


def test_ai_categorize(client):
    token, _ = _register(client)
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/api/v1/ai/categorize",
                    json={"description": "Starbucks latte", "amount": 6.5}, headers=h)
    assert r.json()["category"] == "dining"
