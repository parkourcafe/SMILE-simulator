"""Face detection + mouth landmark extraction (MediaPipe Face Landmarker, 478 pts).

Uses the modern MediaPipe **Tasks** API (`FaceLandmarker`); the 468-point Face Mesh
topology (and our lip indices) is a subset of its output. MediaPipe + the model
bundle are optional (install the ``ml`` extra and provide the model). When either is
missing — e.g. CI or a lightweight container — detection degrades to an approximate
centered mouth region so the pipeline still runs end-to-end; the result flags
``approximate=True`` so callers can decide whether to trust it.

The model bundle path is resolved from ``MEDIAPIPE_FACE_MODEL`` or defaults to
``backend/.cache/face_landmarker.task``. Download it once with:
  curl -L -o backend/.cache/face_landmarker.task \\
    https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task

Landmark indices come from CLAUDE.md (ML Pipeline Details).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

_DEFAULT_MODEL = Path(__file__).resolve().parents[2] / ".cache" / "face_landmarker.task"


def _model_path() -> str | None:
    path = os.environ.get("MEDIAPIPE_FACE_MODEL") or str(_DEFAULT_MODEL)
    return path if os.path.exists(path) else None


# Outer + inner lip contour landmark indices (MediaPipe Face Mesh).
OUTER_LIP = [
    0,
    267,
    269,
    270,
    409,
    291,
    375,
    321,
    405,
    314,
    17,
    84,
    181,
    91,
    146,
    61,
    185,
    40,
    39,
    37,
]
INNER_LIP = [
    78,
    95,
    88,
    178,
    87,
    14,
    317,
    402,
    318,
    324,
    308,
    415,
    310,
    311,
    312,
    13,
    82,
    81,
    80,
    191,
]


class FaceDetectionError(ValueError):
    """Raised when a photo cannot be used (no face / multiple faces)."""


@dataclass
class MouthLandmarks:
    """Pixel-space (x, y) points for the outer mouth contour, plus metadata."""

    outer: list[tuple[int, int]]
    width: int
    height: int
    approximate: bool = False


def _detect_faces(img: Image.Image) -> list | None:
    """Run FaceLandmarker; return a list of faces (each a list of normalized
    landmarks with .x/.y), or None when MediaPipe/model is unavailable."""
    model_path = _model_path()
    if model_path is None:
        return None
    try:
        import mediapipe as mp  # type: ignore
        import numpy as np
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
    except ImportError:
        return None

    rgb = np.ascontiguousarray(np.asarray(img.convert("RGB"), dtype=np.uint8))
    options = vision.FaceLandmarkerOptions(
        # Keep server and headless macOS runs on CPU. An unspecified delegate can
        # initialize a Metal/OpenGL context and abort before Python can recover.
        base_options=mp_python.BaseOptions(
            model_asset_path=model_path,
            delegate=mp_python.BaseOptions.Delegate.CPU,
        ),
        num_faces=2,
    )
    with vision.FaceLandmarker.create_from_options(options) as landmarker:
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect(mp_image)
    return result.face_landmarks or []


def _try_mediapipe(img: Image.Image) -> MouthLandmarks | None:
    """Detect the mouth at the image's native resolution (no crop). Kept for callers
    that already supply a face-centered image."""
    faces = _detect_faces(img)
    if faces is None:
        return None
    if len(faces) == 0:
        raise FaceDetectionError("no_face")
    if len(faces) > 1:
        raise FaceDetectionError("multiple_faces")
    w, h = img.size
    lm = faces[0]
    outer = [(int(lm[i].x * w), int(lm[i].y * h)) for i in OUTER_LIP]
    return MouthLandmarks(outer=outer, width=w, height=h, approximate=False)


def _approximate_mouth(img: Image.Image) -> MouthLandmarks:
    """Heuristic fallback: an ellipse in the lower-center third of a normalized face."""
    w, h = img.size
    cx, cy = w // 2, int(h * 0.72)
    rx, ry = int(w * 0.18), int(h * 0.08)
    outer = [
        (
            cx + int(rx * (1 if i % 2 else -1) * (0.4 + 0.6 * (i % 3) / 2)),
            cy + int(ry * (1 if (i // 2) % 2 else -1)),
        )
        for i in range(12)
    ]
    return MouthLandmarks(outer=outer, width=w, height=h, approximate=True)


def detect_mouth(img: Image.Image) -> MouthLandmarks:
    """Detect exactly one face and return its mouth contour landmarks."""
    landmarks = _try_mediapipe(img)
    if landmarks is not None:
        return landmarks
    return _approximate_mouth(img)


# Square crop padding around the detected face bbox (1.0 = tight, 1.8 = generous).
FACE_CROP_MARGIN = 1.8


def detect_and_crop(img: Image.Image, *, size: int = 1024) -> tuple[Image.Image, MouthLandmarks]:
    """Detect the face, crop a square around it, resize to ``size``, and return the
    cropped image plus mouth landmarks in cropped coordinates.

    This replaces a naive center-crop: phone selfies often have the face off-centre,
    so a center-crop can cut the face out. Falls back to center-crop + approximate
    mouth when MediaPipe/model is unavailable.
    """
    from app.ml import photo  # local import avoids a module cycle at import time

    faces = _detect_faces(img)
    if faces is None:
        crop = photo.normalize(img, size=size)
        return crop, _approximate_mouth(crop)
    if len(faces) == 0:
        raise FaceDetectionError("no_face")
    if len(faces) > 1:
        raise FaceDetectionError("multiple_faces")

    pts = faces[0]
    w, h = img.size
    xs = [p.x * w for p in pts]
    ys = [p.y * h for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    side = max(max(xs) - min(xs), max(ys) - min(ys)) * FACE_CROP_MARGIN
    side = min(side, float(min(w, h)))  # never exceed the image
    left = max(0.0, min(cx - side / 2, w - side))
    top = max(0.0, min(cy - side / 2, h - side))

    crop = img.crop((int(left), int(top), int(left + side), int(top + side)))
    crop = crop.resize((size, size), Image.LANCZOS)

    scale = size / side
    outer = [
        (int((pts[i].x * w - left) * scale), int((pts[i].y * h - top) * scale)) for i in OUTER_LIP
    ]
    return crop, MouthLandmarks(outer=outer, width=size, height=size, approximate=False)
