import pytest

from app.config import Settings
from app.ml.providers import fal
from app.ml.providers.base import InferenceProviderError, ProviderConfig


async def test_fal_fill_uses_supported_payload_and_records_request_id(monkeypatch):
    captured = {}

    class Response:
        status_code = 200
        text = ""
        headers = {"x-fal-request-id": "fal-request-1"}
        content = b"result-image"

        @staticmethod
        def json():
            return {"images": [{"url": "https://files.example.test/result.png"}]}

        @staticmethod
        def raise_for_status():
            return None

    class Client:
        def __init__(self, *, timeout):
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, *, headers, json):
            captured.update(url=url, headers=headers, payload=json)
            return Response()

        async def get(self, url):
            captured["result_url"] = url
            return Response()

    monkeypatch.setattr(fal, "get_settings", lambda: Settings(fal_api_key="fal-test"))
    monkeypatch.setattr(fal.httpx, "AsyncClient", Client)
    provider = fal.FalFluxFillProvider()

    result = await provider.generate(
        image=b"image",
        mask=b"mask",
        prompt="natural smile",
        config=ProviderConfig(image_size=1024),
    )

    assert captured["url"] == "https://fal.run/fal-ai/flux-pro/v1/fill"
    assert captured["payload"]["output_format"] == "png"
    assert captured["payload"]["num_images"] == 1
    assert "num_inference_steps" not in captured["payload"]
    assert "guidance_scale" not in captured["payload"]
    assert captured["result_url"] == "https://files.example.test/result.png"
    assert result.request_id == "fal-request-1"
    assert result.cost_usd == 0.10


async def test_fal_error_does_not_expose_provider_body(monkeypatch):
    class Response:
        status_code = 422
        text = "provider echoed patient@example.test and secret"

    class Client:
        def __init__(self, *, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, _url, *, headers, json):
            return Response()

    monkeypatch.setattr(fal, "get_settings", lambda: Settings(fal_api_key="fal-test"))
    monkeypatch.setattr(fal.httpx, "AsyncClient", Client)

    with pytest.raises(InferenceProviderError) as exc:
        await fal.FalFluxFillProvider().generate(
            image=b"image",
            mask=b"mask",
            prompt="natural smile",
            config=ProviderConfig(image_size=1024),
        )

    assert str(exc.value) == "inference_provider_rejected"
    assert "patient@example.test" not in str(exc.value)
