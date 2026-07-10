from app.config import Settings
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
