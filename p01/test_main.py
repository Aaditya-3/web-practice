import pytest
from httpx import ASGITransport, AsyncClient
from p01.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestProblem1Routing:
    async def test_ping(self, client):
        res = await client.get("/ping")
        assert res.status_code == 200
        assert res.json() == {"message": "pong"}

    async def test_hello_path_param(self, client):
        res = await client.get("/hello/Aaditya")
        assert res.status_code == 200
        assert res.json() == {"greeting": "Hello, Aaditya"}

    @pytest.mark.parametrize(
        "params, expected_sum",
        [
            ({"a": 2, "b": 3}, 5),
            ({"a": -10, "b": 4}, -6),
            ({"a": 1.5, "b": 2.5}, 4.0),
        ],
    )
    async def test_add_valid(self, client, params, expected_sum):
        res = await client.get("/add", params=params)
        assert res.status_code == 200
        assert res.json() == {"sum": expected_sum}

    @pytest.mark.parametrize(
        "params",
        [
            {"a": 2},
            {"b": 3},
            {},
            {"a": "foo", "b": 3},
            {"a": 2, "b": "bar"},
        ],
    )
    async def test_add_invalid(self, client, params):
        res = await client.get("/add", params=params)
        assert res.status_code == 422

    @pytest.mark.parametrize("n, expected", [(4, 16), (-3, 9), (0, 0)])
    async def test_square_valid(self, client, n, expected):
        res = await client.get(f"/square/{n}")
        assert res.status_code == 200
        assert res.json() == {"result": expected}

    @pytest.mark.parametrize("bad_n", ["abc", "3.5"])
    async def test_square_non_int(self, client, bad_n):
        res = await client.get(f"/square/{bad_n}")
        assert res.status_code == 422

    async def test_echo_returns_sent_json(self, client):
        payload = {"user": "dev", "active": True, "scores": [10, 20]}
        res = await client.post("/echo", json=payload)
        assert res.status_code == 200
        assert res.json() == payload

    async def test_health(self, client):
        res = await client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}

    async def test_unknown_route_returns_json_404(self, client):
        res = await client.get("/this-route-does-not-exist")
        assert res.status_code == 404
        assert res.headers["content-type"].startswith("application/json")
        body = res.json()
        assert isinstance(body, dict)
        assert "error" in body or "detail" in body


class TestProblem2Validation:
    async def test_register_valid(self, client):
        payload = {
            "email": "user@example.com",
            "age": 20,
            "password": "strongpassword",
            "confirm_password": "strongpassword",
        }
        res = await client.post("/register", json=payload)
        assert res.status_code == 201
        body = res.json()
        assert body["email"] == "user@example.com"
        assert body["age"] == 20
        assert "password" not in body
        assert "confirm_password" not in body

    @pytest.mark.parametrize(
        "overrides",
        [
            {"email": "not-an-email"},
            {"age": 17},
            {"age": -1},
            {"password": "short", "confirm_password": "short"},
            {"password": "strongpassword", "confirm_password": "differentpassword"},
        ],
    )
    async def test_register_invalid(self, client, overrides):
        payload = {
            "email": "user@example.com",
            "age": 20,
            "password": "strongpassword",
            "confirm_password": "strongpassword",
            **overrides,
        }
        res = await client.post("/register", json=payload)
        assert res.status_code == 422

    async def test_products_valid_with_default_tags(self, client):
        res = await client.post("/products", json={"name": "Keyboard", "price": 2499.50})
        assert res.status_code == 201
        assert res.json() == {"name": "Keyboard", "price": 2499.50, "tags": []}

    async def test_products_valid_with_tags(self, client):
        payload = {"name": "Mouse", "price": 999, "tags": ["wireless", "ergonomic"]}
        res = await client.post("/products", json=payload)
        assert res.status_code == 201
        assert res.json() == payload

    @pytest.mark.parametrize(
        "payload",
        [
            {"name": "", "price": 100},
            {"name": "Keyboard", "price": 0},
            {"name": "Keyboard", "price": -50},
            {"name": "Keyboard", "price": 100, "tags": "not-a-list"},
            {"price": 100},
        ],
    )
    async def test_products_invalid(self, client, payload):
        res = await client.post("/products", json=payload)
        assert res.status_code == 422

    async def test_search_default_limit(self, client):
        res = await client.get("/search", params={"q": "fastapi"})
        assert res.status_code == 200
        assert res.json() == {"q": "fastapi", "limit": 10}

    @pytest.mark.parametrize("limit", [1, 25, 50])
    async def test_search_valid_limits(self, client, limit):
        res = await client.get("/search", params={"q": "python", "limit": limit})
        assert res.status_code == 200
        assert res.json() == {"q": "python", "limit": limit}

    @pytest.mark.parametrize(
        "params",
        [
            {},
            {"q": ""},
            {"q": "python", "limit": 0},
            {"q": "python", "limit": 51},
            {"q": "python", "limit": "ten"},
        ],
    )
    async def test_search_invalid(self, client, params):
        res = await client.get("/search", params=params)
        assert res.status_code == 422


class TestProblem3ErrorEnvelope:
    async def test_malformed_json_returns_400_with_envelope(self, client):
        res = await client.post(
            "/register",
            content='{"email": "user@example.com", "age": ',
            headers={"Content-Type": "application/json"},
        )
        assert res.status_code == 400
        body = res.json()
        assert isinstance(body.get("error"), str) and len(body["error"]) > 0
        assert isinstance(body.get("details"), list) and len(body["details"]) > 0

    async def test_missing_fields_returns_422_with_envelope(self, client):
        res = await client.post("/products", json={})
        assert res.status_code == 422
        body = res.json()
        assert isinstance(body.get("error"), str) and len(body["error"]) > 0
        assert isinstance(body.get("details"), list) and len(body["details"]) >= 2

    async def test_query_validation_error_uses_same_envelope(self, client):
        res = await client.get("/search", params={"q": "fastapi", "limit": 100})
        assert res.status_code == 422
        body = res.json()
        assert isinstance(body.get("error"), str) and len(body["error"]) > 0
        assert isinstance(body.get("details"), list) and len(body["details"]) > 0