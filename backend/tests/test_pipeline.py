import io

import pytest
from PIL import Image

from app.ml import face_mesh, mask, photo
from app.ml.providers.base import GenerationResult


def test_photo_validation_rejects_tiny_image():
    img = Image.new("RGB", (100, 100), (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    with pytest.raises(photo.PhotoValidationError):
        photo.load_and_validate(buf.getvalue())


def test_normalize_produces_square(selfie_bytes):
    img = photo.load_and_validate(selfie_bytes)
    norm = photo.normalize(img, size=512)
    assert norm.size == (512, 512)


def test_mask_is_grayscale_and_has_white_region(selfie_bytes):
    img = photo.normalize(photo.load_and_validate(selfie_bytes), size=512)
    landmarks = face_mesh.detect_mouth(img)
    m = mask.build_mouth_mask(landmarks)
    assert m.mode == "L"
    assert m.getextrema()[1] > 0  # some white pixels exist


@pytest.mark.asyncio
async def test_run_pipeline_with_fake_provider(selfie_bytes, monkeypatch):
    from app.ml import pipeline

    class FakeProvider:
        async def generate(self, *, image, mask, prompt, config):
            # Echo a plausible result so the quality check has something to compare.
            return GenerationResult(
                image=image,
                cost_usd=0.05,
                duration_ms=1234,
                provider="fake",
                request_id="request-test",
            )

    monkeypatch.setattr(pipeline, "get_provider", lambda name=None: FakeProvider())

    out = await pipeline.run_pipeline(
        photo_bytes=selfie_bytes,
        style_template="Beautiful {style} teeth",
        style_name="Natural White",
        apply_watermark=True,
    )
    assert out.provider == "fake"
    assert out.cost_usd == 0.05
    assert out.duration_ms == 1234
    assert out.request_id == "request-test"
    assert 1.0 <= out.quality_score <= 5.0
    # result must be a valid PNG
    Image.open(io.BytesIO(out.result_image)).verify()
