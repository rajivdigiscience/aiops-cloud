import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aiops_hub.models import ApprovalRequest, AuditLogEntry, AuthContext, ProviderName, RoleName, TaskExecutionRequest


class StateStore:
    def __init__(self, db_path: str) -> None:
        Path(db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self.lock:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS approvals (
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    task TEXT NOT NULL,
                    resource_id TEXT,
                    params_json TEXT NOT NULL,
                    requested_by_role TEXT NOT NULL,
                    requested_by_key_fingerprint TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL,
                    review_note TEXT,
                    reviewer_role TEXT,
                    reviewer_key_fingerprint TEXT,
                    created_at TEXT NOT NULL,
                    reviewed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    actor_role TEXT NOT NULL,
                    actor_key_fingerprint TEXT NOT NULL,
                    action TEXT NOT NULL,
                    provider TEXT,
                    task TEXT,
                    status TEXT NOT NULL,
                    details_json TEXT NOT NULL
                );
                """
            )
            self.conn.commit()

    def create_approval(
        self,
        request: TaskExecutionRequest,
        auth: AuthContext,
        reason: str,
    ) -> ApprovalRequest:
        now = _now_iso()
        approval_id = str(uuid.uuid4())
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO approvals (
                    id, provider, task, resource_id, params_json,
                    requested_by_role, requested_by_key_fingerprint,
                    reason, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    approval_id,
                    request.provider,
                    request.task,
                    request.resource_id,
                    json.dumps(request.params),
                    auth.role,
                    auth.key_fingerprint,
                    reason,
                    now,
                ),
            )
            self.conn.commit()

        return self.get_approval_or_raise(approval_id)

    def list_approvals(self, status: str | None = None, limit: int = 100) -> list[ApprovalRequest]:
        query = "SELECT * FROM approvals"
        params: tuple[Any, ...] = ()
        if status:
            query += " WHERE status = ?"
            params = (status,)
        query += " ORDER BY created_at DESC LIMIT ?"
        params = params + (limit,)

        with self.lock:
            rows = self.conn.execute(query, params).fetchall()

        return [self._approval_from_row(row) for row in rows]

    def get_approval(self, approval_id: str) -> ApprovalRequest | None:
        with self.lock:
            row = self.conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        if not row:
            return None
        return self._approval_from_row(row)

    def get_approval_or_raise(self, approval_id: str) -> ApprovalRequest:
        approval = self.get_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval request not found: {approval_id}")
        return approval

    def review_approval(
        self,
        approval_id: str,
        approve: bool,
        note: str,
        reviewer: AuthContext,
    ) -> ApprovalRequest:
        approval = self.get_approval_or_raise(approval_id)
        if approval.status != "pending":
            raise ValueError(f"Approval is already {approval.status}")

        status = "approved" if approve else "rejected"
        reviewed_at = _now_iso()

        with self.lock:
            self.conn.execute(
                """
                UPDATE approvals
                SET status = ?, review_note = ?, reviewer_role = ?, reviewer_key_fingerprint = ?, reviewed_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    note,
                    reviewer.role,
                    reviewer.key_fingerprint,
                    reviewed_at,
                    approval_id,
                ),
            )
            self.conn.commit()

        return self.get_approval_or_raise(approval_id)

    def record_audit(
        self,
        *,
        auth: AuthContext,
        action: str,
        status: str,
        provider: ProviderName | None = None,
        task: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO audit_logs (
                    timestamp, actor_role, actor_key_fingerprint, action,
                    provider, task, status, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _now_iso(),
                    auth.role,
                    auth.key_fingerprint,
                    action,
                    provider,
                    task,
                    status,
                    json.dumps(details or {}),
                ),
            )
            self.conn.commit()

    def list_audit(self, limit: int = 200, action: str | None = None, status: str | None = None) -> list[AuditLogEntry]:
        query = "SELECT * FROM audit_logs"
        filters: list[str] = []
        params: list[Any] = []
        if action:
            filters.append("action = ?")
            params.append(action)
        if status:
            filters.append("status = ?")
            params.append(status)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self.lock:
            rows = self.conn.execute(query, tuple(params)).fetchall()

        return [self._audit_from_row(row) for row in rows]

    @staticmethod
    def _approval_from_row(row: sqlite3.Row) -> ApprovalRequest:
        return ApprovalRequest(
            id=row["id"],
            provider=row["provider"],
            task=row["task"],
            resource_id=row["resource_id"],
            params=json.loads(row["params_json"] or "{}"),
            requested_by_role=row["requested_by_role"],
            requested_by_key_fingerprint=row["requested_by_key_fingerprint"],
            reason=row["reason"],
            status=row["status"],
            review_note=row["review_note"],
            reviewer_role=row["reviewer_role"],
            reviewer_key_fingerprint=row["reviewer_key_fingerprint"],
            created_at=row["created_at"],
            reviewed_at=row["reviewed_at"],
        )

    @staticmethod
    def _audit_from_row(row: sqlite3.Row) -> AuditLogEntry:
        return AuditLogEntry(
            id=row["id"],
            timestamp=row["timestamp"],
            actor_role=row["actor_role"],
            actor_key_fingerprint=row["actor_key_fingerprint"],
            action=row["action"],
            provider=row["provider"],
            task=row["task"],
            status=row["status"],
            details=json.loads(row["details_json"] or "{}"),
        )


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
