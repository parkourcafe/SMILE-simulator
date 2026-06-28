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
