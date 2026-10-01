"""Database operations and schema management for the application."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from datetime import timezone
import sqlite3
from typing import Any, Optional

from app.config import settings

_ALLOWED_JOB_UPDATE_FIELDS: frozenset[str] = frozenset({
    "status",
    "current_node",
    "progress_pct",
    "error",
    "last_message",
    "employee_name",
    "employee_role",
    "customer_id",
})

_SCHEMA: str = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    signup_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    sku TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price_usd REAL NOT NULL,
    wholesale_cost_usd REAL NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    sku TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    status TEXT NOT NULL,
    carrier TEXT,
    estimated_delivery TEXT,
    total_amount_usd REAL NOT NULL,
    fulfillment_center TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (sku) REFERENCES products(sku)
);

CREATE TABLE IF NOT EXISTS sales (
    sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL,
    sale_date TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    revenue_usd REAL NOT NULL,
    fulfillment_center TEXT NOT NULL,
    FOREIGN KEY (sku) REFERENCES products(sku)
);

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    order_id TEXT,
    category TEXT NOT NULL,
    subject TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

CREATE TABLE IF NOT EXISTS refund_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    amount_usd REAL NOT NULL,
    requested_at TEXT NOT NULL,
    approved INTEGER,
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

CREATE TABLE IF NOT EXISTS chat_jobs (
    session_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'queued',
    current_node TEXT,
    progress_pct INTEGER DEFAULT 0,
    error TEXT,
    last_message TEXT,
    employee_name TEXT,
    employee_role TEXT,
    customer_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    approved INTEGER NOT NULL,
    reviewer TEXT NOT NULL,
    comments TEXT,
    decided_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS guardrail_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    rail_type TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT,
    occurred_at TEXT NOT NULL
);
"""


def _current_timestamp_iso() -> str:
  """Returns the current UTC timestamp formatted as an ISO-8601 string."""
  return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn() -> Generator[sqlite3.Connection, None, None]:
  """Yields a managed SQLite connection configured with Row factory."""
  conn = sqlite3.connect(settings.SQLITE_DB_PATH, timeout=10)
  conn.row_factory = sqlite3.Row
  try:
    yield conn
    conn.commit()
  finally:
    conn.close()


def init_db() -> None:
  """Initializes the database schema and performs schema migrations."""
  with get_conn() as conn:
    conn.executescript(_SCHEMA)
    _migrate_add_missing_columns(conn)


def _migrate_add_missing_columns(conn: sqlite3.Connection) -> None:
  """Adds newer chat_jobs columns safely to existing tables."""
  cursor = conn.execute("PRAGMA table_info(chat_jobs)")
  existing_cols = {row["name"] for row in cursor.fetchall()}

  new_columns = ("employee_name", "employee_role", "customer_id")
  for col in new_columns:
    if col not in existing_cols:
      conn.execute(f"ALTER TABLE chat_jobs ADD COLUMN {col} TEXT")

# Jobs
def create_job(
    session_id: str,
    last_message: str,
    employee_name: str = "",
    employee_role: str = "",
    customer_id: str = "",
) -> None:
  """Creates or replaces a chat job row."""
  now = _current_timestamp_iso()
  query = """
      INSERT INTO chat_jobs (
          session_id,
          status,
          last_message,
          employee_name,
          employee_role,
          customer_id,
          created_at,
          updated_at
      )
      VALUES (?, 'queued', ?, ?, ?, ?, ?, ?)
      ON CONFLICT(session_id)
      DO UPDATE SET
          status='queued',
          last_message=excluded.last_message,
          employee_name=excluded.employee_name,
          employee_role=excluded.employee_role,
          customer_id=excluded.customer_id,
          updated_at=excluded.updated_at
  """
  params = (
      session_id,
      last_message,
      employee_name,
      employee_role,
      customer_id,
      now,
      now,
  )
  with get_conn() as conn:
    conn.execute(query, params)


def update_job(session_id: str, **fields: Any) -> None:
  """Updates specific fields of an existing chat job.

  Args:
      session_id: Identifier of the target session.
      **fields: Field-value pairs to update.

  Raises:
      ValueError: If any field name is not recognized or permitted.
  """
  if not fields:
    return

  invalid_fields = set(fields.keys()) - _ALLOWED_JOB_UPDATE_FIELDS
  if invalid_fields:
    raise ValueError(f"Disallowed fields in update_job: {invalid_fields}")

  fields["updated_at"] = _current_timestamp_iso()
  set_clauses = ", ".join(f"{key} = ?" for key in fields)
  params = (*fields.values(), session_id)

  query = f"UPDATE chat_jobs SET {set_clauses} WHERE session_id = ?"
  with get_conn() as conn:
    conn.execute(query, params)


def get_job(session_id: str) -> Optional[sqlite3.Row]:
  """Retrieves a single chat job by session ID."""
  query = "SELECT * FROM chat_jobs WHERE session_id = ?"
  with get_conn() as conn:
    return conn.execute(query, (session_id,)).fetchone()


def list_jobs(limit: int = 50) -> list[sqlite3.Row]:
  """Returns recently created chat jobs ordered chronologically descending."""
  query = "SELECT * FROM chat_jobs ORDER BY created_at DESC LIMIT ?"
  with get_conn() as conn:
    return conn.execute(query, (limit,)).fetchall()

# Approvals

def record_approval(
    session_id: str,
    approved: bool,
    reviewer: str,
    comments: Optional[str],
) -> None:
  """Persists a human-in-the-loop review decision."""
  query = """
      INSERT INTO approvals (
          session_id,
          approved,
          reviewer,
          comments,
          decided_at
      )
      VALUES (?, ?, ?, ?, ?)
  """
  params = (
      session_id,
      int(approved),
      reviewer,
      comments,
      _current_timestamp_iso(),
  )
  with get_conn() as conn:
    conn.execute(query, params)

# Guardrail audit log

def log_guardrail_event(
    session_id: Optional[str],
    rail_type: str,
    action: str,
    detail: str,
) -> None:
  """Logs a guardrail execution event for audit trails."""
  query = """
      INSERT INTO guardrail_events (
          session_id,
          rail_type,
          action,
          detail,
          occurred_at
      )
      VALUES (?, ?, ?, ?, ?)
  """
  params = (session_id, rail_type, action, detail, _current_timestamp_iso())
  with get_conn() as conn:
    conn.execute(query, params)


def list_guardrail_events(
    limit: int = 100,
    session_id: Optional[str] = None,
) -> list[sqlite3.Row]:
  """Returns audit events, optionally filtered by session ID."""
  with get_conn() as conn:
    if session_id:
      query = """
          SELECT *
          FROM guardrail_events
          WHERE session_id = ?
          ORDER BY occurred_at DESC
          LIMIT ?
      """
      return conn.execute(query, (session_id, limit)).fetchall()

    query = """
        SELECT *
        FROM guardrail_events
        ORDER BY occurred_at DESC
        LIMIT ?
    """
    return conn.execute(query, (limit,)).fetchall()


# -----------------------------------------------------------------------------
# Refund approval persistence and anomaly detection
# -----------------------------------------------------------------------------


def record_refund_request(
    order_id: str,
    customer_id: str,
    amount_usd: float,
) -> None:
  """Records a new refund request if an identical approved one does not exist."""
  existing = get_existing_approved_refund(
      order_id=order_id,
      customer_id=customer_id,
      amount_usd=amount_usd,
  )
  if existing:
    return

  query = """
      INSERT INTO refund_requests (
          order_id,
          customer_id,
          amount_usd,
          requested_at
      )
      VALUES (?, ?, ?, ?)
  """
  params = (order_id, customer_id, amount_usd, _current_timestamp_iso())
  with get_conn() as conn:
    conn.execute(query, params)


def get_existing_approved_refund(
    order_id: str,
    customer_id: str,
    amount_usd: float,
) -> Optional[sqlite3.Row]:
  """Finds an existing approved refund matching order, customer, and amount."""
  query = """
      SELECT *
      FROM refund_requests
      WHERE order_id = ?
        AND customer_id = ?
        AND ABS(amount_usd - ?) < 0.01
        AND approved = 1
      ORDER BY requested_at DESC
      LIMIT 1
  """
  with get_conn() as conn:
    return conn.execute(query, (order_id, customer_id, amount_usd)).fetchone()


def get_existing_rejected_refund(
    order_id: str,
    customer_id: str,
    amount_usd: float,
) -> Optional[sqlite3.Row]:
  """Returns the latest rejected matching refund, if present."""
  query = """
      SELECT *
      FROM refund_requests
      WHERE order_id = ?
        AND customer_id = ?
        AND ABS(amount_usd - ?) < 0.01
        AND approved = 0
      ORDER BY requested_at DESC
      LIMIT 1
  """
  with get_conn() as conn:
    return conn.execute(query, (order_id, customer_id, amount_usd)).fetchone()


def update_latest_refund_decision(
    order_id: str,
    customer_id: str,
    amount_usd: float,
    approved: bool,
) -> None:
  """Stores the review decision against the newest matching pending refund."""
  select_query = """
      SELECT id
      FROM refund_requests
      WHERE order_id = ?
        AND customer_id = ?
        AND ABS(amount_usd - ?) < 0.01
        AND approved IS NULL
      ORDER BY requested_at DESC
      LIMIT 1
  """
  with get_conn() as conn:
    row = conn.execute(
        select_query, (order_id, customer_id, amount_usd)
    ).fetchone()
    if not row:
      return

    update_query = "UPDATE refund_requests SET approved = ? WHERE id = ?"
    conn.execute(update_query, (int(approved), row["id"]))


def recent_refund_request_count(
    customer_id: str,
    window_minutes: int = 60,
) -> int:
  """Counts refund requests within a recent time window for anomaly checks."""
  query = """
      SELECT COUNT(*) AS n
      FROM refund_requests
      WHERE customer_id = ?
        AND requested_at >= datetime('now', ?)
  """
  with get_conn() as conn:
    row = conn.execute(query, (customer_id, f"-{window_minutes} minutes")).fetchone()

  return row["n"] if row else 0


# -----------------------------------------------------------------------------
# Domain data lookups
# -----------------------------------------------------------------------------


def get_order(order_id: str) -> Optional[sqlite3.Row]:
  """Fetches an order record by order ID."""
  query = "SELECT * FROM orders WHERE order_id = ?"
  with get_conn() as conn:
    return conn.execute(query, (order_id,)).fetchone()


def get_product(sku: str) -> Optional[sqlite3.Row]:
  """Fetches product details by SKU."""
  query = "SELECT * FROM products WHERE sku = ?"
  with get_conn() as conn:
    return conn.execute(query, (sku,)).fetchone()


def get_customer_orders(customer_id: str) -> list[sqlite3.Row]:
  """Returns all orders placed by a customer ordered by date descending."""
  query = """
      SELECT *
      FROM orders
      WHERE customer_id = ?
      ORDER BY order_date DESC
  """
  with get_conn() as conn:
    return conn.execute(query, (customer_id,)).fetchall()