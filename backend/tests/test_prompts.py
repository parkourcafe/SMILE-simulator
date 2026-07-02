from app.ml.prompts import SAFETY_SUFFIX, build_prompt


def test_template_with_safety_language_kept_verbatim():
    template = (
        "Beautiful naturally white teeth, photorealistic, preserve original lip shape and lighting"
    )
    assert build_prompt(template, style_name="Natural White") == template


def test_safety_suffix_appended_when_missing():
    out = build_prompt("Whiter teeth", style_name="Natural White")
    assert out.endswith(SAFETY_SUFFIX)
    assert out.startswith("Whiter teeth")


def test_style_placeholder_interpolated():
    out = build_prompt("Beautiful {style} teeth", style_name="Hollywood")
    assert "Hollywood" in out


def test_unknown_placeholder_left_intact():
    out = build_prompt("teeth {unknown}", style_name="X")
    assert "{unknown}" in out
