"""Face detection + mouth landmark extraction (MediaPipe Face Mesh, 468 landmarks).

MediaPipe is an optional dependency (install with the ``ml`` extra). When it is not
present — e.g. in CI or a lightweight container — detection degrades to an
approximate centered mouth region so the pipeline still runs end-to-end. The result
flags ``approximate=True`` in that case so callers can decide whether to trust it.

Landmark indices come from CLAUDE.md (ML Pipeline Details).
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

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


def _try_mediapipe(img: Image.Image) -> MouthLandmarks | None:
    try:
        import mediapipe as mp  # type: ignore
        import numpy as np
    except ImportError:
        return None

    w, h = img.size
    rgb = np.asarray(img.convert("RGB"))
    mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True, max_num_faces=2, refine_landmarks=True
    )
    try:
        result = mesh.process(rgb)
    finally:
        mesh.close()

    faces = result.multi_face_landmarks or []
    if len(faces) == 0:
        raise FaceDetectionError("no_face")
    if len(faces) > 1:
        # Architecture §13 open question — for MVP we reject multi-face photos.
        raise FaceDetectionError("multiple_faces")

    lm = faces[0].landmark
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
