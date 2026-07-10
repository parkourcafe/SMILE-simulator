from app.config import Settings
from app.services import supabase_client
from app.services.supabase_client import SupabaseClient


def test_headers_omit_profile_for_public_schema():
    sb = SupabaseClient(Settings(supabase_db_schema="public"))
    headers = sb._headers()
    assert "Accept-Profile" not in headers
    assert "Content-Profile" not in headers


def test_headers_set_profile_for_namespaced_schema():
    sb = SupabaseClient(Settings(supabase_db_schema="smile"))
    headers = sb._headers()
    assert headers["Accept-Profile"] == "smile"
    assert headers["Content-Profile"] == "smile"


def test_current_secret_key_is_not_sent_as_bearer_token():
    sb = SupabaseClient(Settings(supabase_secret_key="sb_secret_backend_test"))
    headers = sb._headers()
    assert headers["apikey"] == "sb_secret_backend_test"
    assert "Authorization" not in headers


def test_legacy_service_role_key_keeps_bearer_header():
    sb = SupabaseClient(Settings(supabase_service_role_key="legacy-service-role-jwt"))
    headers = sb._headers()
    assert headers["apikey"] == "legacy-service-role-jwt"
    assert headers["Authorization"] == "Bearer legacy-service-role-jwt"


async def test_remove_objects_uses_storage_delete_api(monkeypatch):
    captured = {}

    class Response:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return [{"name": "user/result.png"}]

    class Client:
        def __init__(self, *, timeout):
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def request(self, method, url, *, headers, json):
            captured.update(method=method, url=url, headers=headers, json=json)
            return Response()

    monkeypatch.setattr(supabase_client.httpx, "AsyncClient", Client)
    sb = SupabaseClient(
        Settings(
            supabase_url="https://project.supabase.co",
            supabase_secret_key="sb_secret_backend_test",
            supabase_storage_bucket="photos",
        )
    )
    result = await sb.remove_objects(["user/result.png", "user/result.png", ""])

    assert result == [{"name": "user/result.png"}]
    assert captured["method"] == "DELETE"
    assert captured["url"] == "https://project.supabase.co/storage/v1/object/photos"
    assert captured["json"] == {"prefixes": ["user/result.png"]}
    assert "Authorization" not in captured["headers"]


async def test_ping_uses_a_bounded_schema_query(monkeypatch):
    captured = {"requests": []}

    class Response:
        status_code = 200

    class Client:
        def __init__(self, *, timeout):
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url, *, headers, params):
            captured["requests"].append((url, headers, params))
            return Response()

        async def post(self, url, *, headers, json):
            captured["rpc"] = (url, headers, json)
            return Response()

    monkeypatch.setattr(supabase_client.httpx, "AsyncClient", Client)
    sb = SupabaseClient(
        Settings(
            supabase_url="https://project.supabase.co",
            supabase_secret_key="sb_secret_backend_test",
        )
    )

    await sb.ping()

    assert captured["timeout"] == 5
    assert [request[0].rsplit("/", 1)[-1] for request in captured["requests"]] == [
        "styles",
        "generations",
        "photo_processing_consents",
        "leads",
        "clinic_api_keys",
    ]
    assert captured["requests"][1][2] == {
        "select": "id,photo_consent_id,quota_state",
        "limit": "1",
    }
    assert captured["rpc"][0].endswith("/rpc/reserve_generation_quota")
    assert captured["rpc"][2]["p_rate_limit"] == 1


async def test_rpc_posts_service_function_parameters(monkeypatch):
    captured = {}

    class Response:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"allowed": False, "reason": "limit_reached"}

    class Client:
        def __init__(self, *, timeout):
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, *, headers, json):
            captured.update(url=url, headers=headers, json=json)
            return Response()

    monkeypatch.setattr(supabase_client.httpx, "AsyncClient", Client)
    sb = SupabaseClient(
        Settings(
            supabase_url="https://project.supabase.co",
            supabase_secret_key="sb_secret_backend_test",
        )
    )

    result = await sb.rpc("reserve_generation_quota", {"p_user_id": "user-1"})

    assert result == {"allowed": False, "reason": "limit_reached"}
    assert captured["timeout"] == 15
    assert captured["url"] == ("https://project.supabase.co/rest/v1/rpc/reserve_generation_quota")
    assert captured["json"] == {"p_user_id": "user-1"}
    assert "Authorization" not in captured["headers"]
