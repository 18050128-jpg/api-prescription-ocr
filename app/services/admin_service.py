from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.user_service import USER_DB_PATH

DATABASE_DIR = USER_DB_PATH.parent
PRESCRIPTIONS_PATH = DATABASE_DIR / "Prescriptions.json"
AUDIT_LOG_PATH = DATABASE_DIR / "AuditLog.json"


def _read_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def _write_list(path: Path, data: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def record_audit(actor: dict[str, Any], action: str, target: str = "", detail: str = "") -> None:
    logs = _read_list(AUDIT_LOG_PATH)
    logs.insert(0, {
        "id": f"audit-{datetime.now(timezone.utc).timestamp()}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "actor_username": actor.get("username", "unknown"),
        "action": action,
        "target": target,
        "detail": detail,
    })
    _write_list(AUDIT_LOG_PATH, logs[:200])


def get_admin_stats() -> dict[str, Any]:
    users = _read_list(USER_DB_PATH)
    prescriptions = _read_list(PRESCRIPTIONS_PATH)
    reviewed = 0
    for prescription in prescriptions:
        confidence = (prescription.get("data") or {}).get("ocr", {}).get("do_tin_cay_trung_binh")
        try:
            if confidence is not None and float(confidence) < 0.75:
                reviewed += 1
        except (TypeError, ValueError):
            reviewed += 1

    total_prescriptions = len(prescriptions)
    return {
        "total_users": len(users),
        "active_users": sum(1 for user in users if user.get("is_active", True)),
        "total_prescriptions": total_prescriptions,
        "total_ocr": total_prescriptions,
        "ocr_needs_review": reviewed,
        "ocr_review_rate": round((reviewed / total_prescriptions) * 100, 2) if total_prescriptions else 0,
        "users_by_role": {
            role: sum(1 for user in users if user.get("role") == role)
            for role in ("user", "doctor", "pharmacist", "admin")
        },
    }


def get_audit_logs(limit: int = 20) -> list[dict[str, Any]]:
    return _read_list(AUDIT_LOG_PATH)[:limit]
