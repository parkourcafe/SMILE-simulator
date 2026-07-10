"""Auditable input and score evidence for the standardized Phase 0 run."""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

CRITERIA = (
    "tooth_realism",
    "face_preservation",
    "boundary_blending",
    "style_accuracy",
    "emotional_response",
)
TRUE_VALUES = {"1", "true", "yes"}
EXPECTED_FACE_MODEL_SHA256 = "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"
EXPECTED_ENDPOINT = "fal-ai/flux-pro/v1/fill"


class EvidenceError(ValueError):
    """Raised when a run cannot produce valid Phase 0 evidence."""


@dataclass(frozen=True)
class ConsentRecord:
    file: str
    consent_version: str
    consented_at: date
    deletion_due_at: date


@dataclass(frozen=True)
class InputEvidence:
    file: str
    sha256: str
    byte_size: int
    width: int
    height: int
    face_approximate: bool
    consent_confirmed: bool
    consent_version: str
    consented_at: str
    deletion_due_at: str


@dataclass(frozen=True)
class Evaluation:
    decision: str
    overall_average: float
    criterion_averages: dict[str, float]
    attempted: int
    succeeded: int
    failed: int
    styles: tuple[str, ...]
    providers: tuple[str, ...]
    total_cost_usd: float
    average_duration_ms: float
    request_ids_captured: int
    reasons: tuple[str, ...]
    score_rows: tuple[dict[str, str], ...]
    evidence_checksums: dict[str, str]
    run_configuration: dict


def collect_images(input_dir: Path, image_exts: set[str]) -> list[Path]:
    images = sorted(path for path in input_dir.iterdir() if path.suffix.lower() in image_exts)
    if not images:
        raise EvidenceError(f"No images found in {input_dir}")
    return images


def load_consent_manifest(
    path: Path,
    filenames: set[str],
    *,
    today: date | None = None,
) -> dict[str, ConsentRecord]:
    required = {
        "file",
        "consent_confirmed",
        "consent_version",
        "consented_at",
        "deletion_due_at",
    }
    today = today or date.today()
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise EvidenceError(f"Consent manifest must contain {sorted(required)}")
            rows = list(reader)
    except OSError as exc:
        raise EvidenceError(f"Cannot read consent manifest: {path}") from exc

    records: dict[str, ConsentRecord] = {}
    for row in rows:
        filename = (row.get("file") or "").strip()
        if filename in records:
            raise EvidenceError(f"Duplicate consent row: {filename}")
        if (row.get("consent_confirmed") or "").strip().lower() not in TRUE_VALUES:
            raise EvidenceError(f"Consent is not confirmed for {filename}")
        version = (row.get("consent_version") or "").strip()
        if not version:
            raise EvidenceError(f"Consent version is missing for {filename}")
        try:
            consented_at = date.fromisoformat((row.get("consented_at") or "").strip())
            deletion_due_at = date.fromisoformat((row.get("deletion_due_at") or "").strip())
        except ValueError as exc:
            raise EvidenceError(f"Consent dates must be ISO YYYY-MM-DD for {filename}") from exc
        if consented_at > today:
            raise EvidenceError(f"Consent date is in the future for {filename}")
        if deletion_due_at < today:
            raise EvidenceError(f"Deletion date has already passed for {filename}")
        if deletion_due_at > consented_at + timedelta(days=30):
            raise EvidenceError(f"Deletion date exceeds 30 days for {filename}")
        records[filename] = ConsentRecord(
            file=filename,
            consent_version=version,
            consented_at=consented_at,
            deletion_due_at=deletion_due_at,
        )

    missing = filenames - records.keys()
    unexpected = records.keys() - filenames
    if missing or unexpected:
        raise EvidenceError(
            f"Consent/image mismatch; missing={sorted(missing)}, unexpected={sorted(unexpected)}"
        )
    return records


def build_input_evidence(
    images: list[Path],
    *,
    inspect_image: Callable[[Path], tuple[int, int, bool]],
    consents: dict[str, ConsentRecord] | None,
    expected_count: int | None = 10,
    require_real_landmarks: bool = True,
) -> list[InputEvidence]:
    if expected_count is not None and len(images) != expected_count:
        raise EvidenceError(
            f"Phase 0 requires exactly {expected_count} images; found {len(images)}"
        )

    records: list[InputEvidence] = []
    seen_hashes: dict[str, str] = {}
    for path in images:
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest in seen_hashes:
            raise EvidenceError(f"Exact duplicate images: {seen_hashes[digest]} and {path.name}")
        seen_hashes[digest] = path.name
        try:
            width, height, approximate = inspect_image(path)
        except (OSError, ValueError) as exc:
            raise EvidenceError(f"Image preflight failed for {path.name}: {exc}") from exc
        if require_real_landmarks and approximate:
            raise EvidenceError(f"Real Face Landmarker is unavailable for {path.name}")
        consent = consents.get(path.name) if consents else None
        if consents is not None and consent is None:
            raise EvidenceError(f"Consent is missing for {path.name}")
        records.append(
            InputEvidence(
                file=path.name,
                sha256=digest,
                byte_size=len(data),
                width=width,
                height=height,
                face_approximate=approximate,
                consent_confirmed=consent is not None,
                consent_version=consent.consent_version if consent else "",
                consented_at=consent.consented_at.isoformat() if consent else "",
                deletion_due_at=consent.deletion_due_at.isoformat() if consent else "",
            )
        )
    return records


def write_input_manifest(path: Path, records: list[InputEvidence]) -> None:
    fields = list(InputEvidence.__dataclass_fields__)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: getattr(record, field) for field in fields} for record in records)


def _read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
    except OSError as exc:
        raise EvidenceError(f"Cannot read {path}") from exc


def _validate_run_artifacts(
    results_path: Path,
    scorecard_path: Path,
    results: list[dict[str, str]],
) -> tuple[bool, tuple[str, ...], dict[str, str], dict]:
    directory = results_path.parent
    paths = {
        "input_manifest.csv": directory / "input_manifest.csv",
        "run_config.json": directory / "run_config.json",
        "results.csv": results_path,
        "scorecard.csv": scorecard_path,
    }
    checksums: dict[str, str] = {}
    issues: list[str] = []
    for name, path in paths.items():
        if not path.is_file():
            issues.append(f"Required evidence file is missing: {name}")
            continue
        checksums[name] = hashlib.sha256(path.read_bytes()).hexdigest()

    config: dict = {}
    manifest: list[dict[str, str]] = []
    if paths["run_config.json"].is_file():
        try:
            config = json.loads(paths["run_config.json"].read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            issues.append("run_config.json is invalid")
    if paths["input_manifest.csv"].is_file():
        manifest = _read_csv(paths["input_manifest.csv"])

    result_styles = sorted({row.get("style", "") for row in results})
    if (
        config.get("dry_run") is not False
        or config.get("watermark") is not False
        or config.get("source_dirty") is not False
        or config.get("source_commit") in {None, "", "unknown"}
        or config.get("input_count") != 10
        or config.get("styles") != result_styles
        or config.get("face_model_sha256") != EXPECTED_FACE_MODEL_SHA256
        or config.get("endpoint") != EXPECTED_ENDPOINT
        or config.get("result_image_size") != 1024
    ):
        issues.append("run_config.json does not describe a clean standardized real run")

    if len(manifest) != 10:
        issues.append("input_manifest.csv must contain exactly 10 rows")
    else:
        if any((row.get("consent_confirmed") or "").lower() not in TRUE_VALUES for row in manifest):
            issues.append("input_manifest.csv contains an unconsented input")
        if any((row.get("face_approximate") or "").lower() in TRUE_VALUES for row in manifest):
            issues.append("input_manifest.csv contains an approximate face mask")
        if any(
            not row.get("consent_version")
            or not row.get("consented_at")
            or not row.get("deletion_due_at")
            for row in manifest
        ):
            issues.append("input_manifest.csv contains incomplete consent metadata")
        manifest_hashes = {(row.get("file"), row.get("sha256")) for row in manifest}
        if len(manifest_hashes) != 10:
            issues.append("input_manifest.csv contains duplicate file/hash evidence")
        result_hashes = {(row.get("file"), row.get("input_sha256")) for row in results}
        if manifest_hashes != result_hashes:
            issues.append("Input hashes in results.csv do not match input_manifest.csv")

    return not issues, tuple(issues), checksums, config


def evaluate_scorecard(
    results_path: Path,
    scorecard_path: Path,
    *,
    recurring_identity_failure: bool = False,
) -> Evaluation:
    results = _read_csv(results_path)
    scores = _read_csv(scorecard_path)
    if not results:
        raise EvidenceError("results.csv is empty")

    successful = [row for row in results if row.get("status") == "ok"]
    if not successful:
        raise EvidenceError("No successful generations to score")
    expected_keys = {(row["file"], row["style"]) for row in successful}
    score_by_key: dict[tuple[str, str], dict[str, str]] = {}
    numeric: dict[tuple[str, str], dict[str, float]] = {}
    for row in scores:
        key = ((row.get("file") or "").strip(), (row.get("style") or "").strip())
        if key in score_by_key:
            raise EvidenceError(f"Duplicate score row: {key}")
        ratings: dict[str, float] = {}
        for criterion in CRITERIA:
            try:
                value = float(row.get(criterion) or "")
            except ValueError as exc:
                raise EvidenceError(f"Missing or invalid {criterion} for {key}") from exc
            if not 1.0 <= value <= 5.0:
                raise EvidenceError(f"{criterion} must be between 1 and 5 for {key}")
            ratings[criterion] = value
        score_by_key[key] = row
        numeric[key] = ratings

    missing = expected_keys - score_by_key.keys()
    unexpected = score_by_key.keys() - expected_keys
    if missing or unexpected:
        raise EvidenceError(
            f"Score/result mismatch; missing={sorted(missing)}, unexpected={sorted(unexpected)}"
        )

    criterion_averages = {
        criterion: round(mean(ratings[criterion] for ratings in numeric.values()), 2)
        for criterion in CRITERIA
    }
    overall = round(mean(criterion_averages.values()), 2)
    attempts = len(results)
    failures = attempts - len(successful)
    styles = tuple(sorted({row["style"] for row in results}))
    providers = tuple(
        sorted({row.get("provider", "") for row in successful if row.get("provider")})
    )
    request_ids_captured = sum(1 for row in successful if row.get("request_id"))
    artifacts_valid, artifact_issues, evidence_checksums, run_configuration = (
        _validate_run_artifacts(results_path, scorecard_path, results)
    )
    standard_run = (
        attempts == 10
        and len(styles) == 1
        and providers == ("fal_flux_pro_fill",)
        and request_ids_captured == len(successful)
        and artifacts_valid
    )
    minimum_criterion = min(criterion_averages.values())

    reasons: list[str] = []
    if recurring_identity_failure:
        decision = "NO-GO"
        reasons.append("Recurring identity/face-preservation failure was confirmed by review.")
    elif overall < 3.0:
        decision = "NO-GO"
        reasons.append("Overall average is below 3.0.")
    elif overall >= 3.5 and minimum_criterion >= 2.0 and failures == 0 and standard_run:
        decision = "GO"
        reasons.append("All quantitative GO thresholds passed on the standardized 10-image run.")
    else:
        decision = "ITERATE"
        if overall < 3.5:
            reasons.append("Overall average is below 3.5.")
        if minimum_criterion < 2.0:
            reasons.append("At least one criterion average is below 2.0.")
        if failures:
            reasons.append(f"{failures} generation(s) failed and therefore block GO.")
        if request_ids_captured != len(successful):
            reasons.append("Not every successful generation has a provider request ID.")
        if providers != ("fal_flux_pro_fill",):
            reasons.append("The run did not use only the approved Fal.ai provider.")
        reasons.extend(artifact_issues)
        if not standard_run:
            reasons.append("Evidence is not a one-style, exactly 10-generation run.")

    durations = [int(float(row.get("duration_ms") or 0)) for row in successful]
    return Evaluation(
        decision=decision,
        overall_average=overall,
        criterion_averages=criterion_averages,
        attempted=attempts,
        succeeded=len(successful),
        failed=failures,
        styles=styles,
        providers=providers,
        total_cost_usd=round(sum(float(row.get("cost_usd") or 0) for row in results), 4),
        average_duration_ms=round(mean(durations), 1),
        request_ids_captured=request_ids_captured,
        reasons=tuple(reasons),
        score_rows=tuple(score_by_key[key] for key in sorted(score_by_key)),
        evidence_checksums=evidence_checksums,
        run_configuration=run_configuration,
    )


def render_report(evaluation: Evaluation, *, now: datetime | None = None) -> str:
    now = now or datetime.now(ZoneInfo("Asia/Makassar"))
    stamp = now.strftime("%d.%m.%Y | %H:%M | Bali")
    face_model_sha = evaluation.run_configuration.get("face_model_sha256", "unknown")
    lines = [
        "# ZubiLook Phase 0 Go/No-Go Report",
        "",
        f"> Created: {stamp}",
        f"> Decision: **{evaluation.decision}**",
        "",
        "## Run evidence",
        "",
        f"- Attempts: {evaluation.attempted}",
        f"- Successful: {evaluation.succeeded}",
        f"- Failed: {evaluation.failed}",
        f"- Style(s): {', '.join(evaluation.styles)}",
        f"- Provider(s): {', '.join(evaluation.providers) or 'unknown'}",
        f"- Request IDs captured: {evaluation.request_ids_captured}/{evaluation.succeeded}",
        f"- Total measured cost: ${evaluation.total_cost_usd:.4f}",
        f"- Mean measured latency: {evaluation.average_duration_ms:.1f} ms",
        f"- Source commit: `{evaluation.run_configuration.get('source_commit', 'unknown')}`",
        f"- Face model SHA-256: `{face_model_sha}`",
        f"- Endpoint: `{evaluation.run_configuration.get('endpoint', 'unknown')}`",
        f"- Result size: {evaluation.run_configuration.get('result_image_size', 'unknown')}",
        "",
        "## Evidence files",
        "",
        "| File | SHA-256 |",
        "|---|---|",
    ]
    lines.extend(
        f"| {name} | `{checksum}` |" for name, checksum in evaluation.evidence_checksums.items()
    )
    lines.extend(
        [
            "",
            "## Quality scores",
            "",
            f"Overall average: **{evaluation.overall_average:.2f}/5**",
            "",
            "| Criterion | Average |",
            "|---|---:|",
        ]
    )
    lines.extend(
        f"| {criterion.replace('_', ' ').title()} | {average:.2f} |"
        for criterion, average in evaluation.criterion_averages.items()
    )
    lines.extend(["", "## Decision reasons", ""])
    lines.extend(f"- {reason}" for reason in evaluation.reasons)
    lines.extend(
        [
            "",
            "## Score matrix",
            "",
            (
                "| File | Style | Tooth realism | Face preservation | Boundary blending | "
                "Style accuracy | Emotional response | Row average | Notes |"
            ),
            "|---|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in evaluation.score_rows:
        values = [float(row[criterion]) for criterion in CRITERIA]
        notes = (row.get("notes") or "").replace("|", "\\|")
        lines.append(
            f"| {row['file']} | {row['style']} | "
            + " | ".join(f"{value:.1f}" for value in values)
            + f" | {mean(values):.2f} | {notes} |"
        )
    lines.extend(
        [
            "",
            "## Fixed decision rule",
            "",
            (
                "- GO: exactly 10/10 successful generations with one fixed style, "
                "overall average at least 3.5, every criterion average at least 2.0, "
                "and no recurring identity failure."
            ),
            (
                "- ITERATE: overall average 3.0-3.49, a criterion below 2.0, any "
                "failed generation, or non-standard evidence."
            ),
            (
                "- NO-GO: overall average below 3.0 or confirmed recurring "
                "identity/face-preservation failure."
            ),
            "",
            "This is a product-quality test, not clinical evidence or a medical evaluation.",
            "",
        ]
    )
    return "\n".join(lines)
