# DataForge — The Moat

*Design document. Last updated April 2026.*

---

## The Moat in One Paragraph

The moat is not data generation. Any LLM can generate data. The moat is the **iterative refinement loop**: a user describes a dataset, sees it rendered live, issues a natural language command to change it, and sees exactly what changed — with the ability to undo, re-run, and export at any point. No existing tool does this. Tools like Mockaroo, Gretel, and Mostly AI treat generation as a one-shot export action. DataForge treats the dataset as a living artifact the user sculpts over a session. The technical substance of this moat is three things that compound: an **operation model** (a precise vocabulary of dataset mutations an LLM can reliably output), a **dataset session** (a structured in-memory representation of what the user is building that persists across turns), and a **patch-first UI** (the user sees operations applied incrementally, not a full re-render). These three together produce the experience. Building any one of them is easy. Wiring all three together into a fluid loop is the work.

---

## The Cursor Analogy, Mapped Precisely

Cursor's real innovation was not using GPT-4 for code. It was making the agent's output **structurally traceable** back to a known artifact.

| Cursor concept | DataForge equivalent |
|---|---|
| Source file | Dataset state (schema + rows + stats) |
| File edit / diff | Dataset operation (typed mutation) |
| Diff view (accept/reject) | Operation preview + undo |
| Context window (current file + imports) | Schema + column stats + sample rows |
| Language server (syntax awareness) | Statistical coherence engine |
| Conversation memory (Composer) | Dataset session with intent summary |
| Multi-file edit | Cross-table operation with FK integrity |

The key property Cursor has that makes this work: **the agent never returns free-form text that gets parsed into file changes**. It returns structured edits (unified diff or replace blocks) that are applied deterministically. DataForge needs the same property for data: the agent returns structured operations, not raw generated rows.

---

## What "Cursor for Data" Actually Requires

These are the hard parts. Data has properties code does not, which makes several of them genuinely novel problems.

### 1. Statistical coherence across operations

When Cursor adds a method to a class, the new method does not need to be statistically correlated with the existing methods. When DataForge adds a `customer_lifetime_value` column to a table that already has `purchase_frequency` and `avg_order_value`, the new column must be statistically coherent with both. Its distribution, correlation, and null rate must fit the existing dataset — not be generated independently.

This is the hardest problem in the loop. It requires that every add/modify operation is aware of the existing column statistics before generating values.

### 2. Operations are not idempotent by default

In code, applying the same diff twice produces a conflict. In data, applying the same operation twice (e.g. "inject 50 outlier rows") should either be idempotent or produce a clear version branch. The operation log must track this, and the UI must make it visible.

### 3. The agent's context window is not the dataset

A dataset of 100k rows is not going to fit in a context window. The agent must reason about the dataset from a **statistical summary**, not the raw data. This means the dataset session object must maintain live column statistics (min/max/mean/stddev/cardinality/null rate/sample values) that the agent can reason from. The agent never sees the rows. It sees the schema and the stats.

### 4. Referential integrity across operations

Adding a column to a child table that references a parent table's primary key requires the operation to know about that relationship. Any operation that touches a column involved in a foreign key relationship must propagate the constraint. This is not required for MVP but the data model must accommodate it from the start.

---

## The Operation Model

This is the core technical artifact. It does not exist yet.

An operation is a typed, serializable description of a single mutation to the dataset state. The agent outputs a list of operations. The backend applies them deterministically. The frontend renders the diff.

### Operation vocabulary

```
# Structural
AddColumn(table, name, type, description, constraints)
RemoveColumn(table, name)
RenameColumn(table, old_name, new_name)
AddTable(name, schema, row_count)
AddRelationship(child_table, child_col, parent_table, parent_col)

# Distribution
SetDistribution(table, column, distribution: DistributionSpec)
CorrelateColumns(table, col_a, col_b, coefficient: float)
SetNullRate(table, column, rate: float)

# Injection
InjectOutliers(table, column, count, outlier_spec: OutlierSpec)
InjectTemporalPattern(table, date_col, value_col, pattern: PatternSpec)
InjectAnomalyWindow(table, date_range, affected_columns, magnitude)

# Row-level
ExpandRows(table, additional_rows: int)
FilterRows(table, condition: str)         # natural language condition, LLM-evaluated
SampleRows(table, n: int, strategy: str)

# Regeneration
RegenerateColumn(table, column)           # re-run with same spec, new seed
RegenerateTable(table)                    # full table, preserve relationships
```

### Operation properties

Every operation must have:
- `operation_id: uuid` — for undo/redo tracking
- `table: str` — affected table(s)
- `applied_at: datetime`
- `agent_reasoning: str` — why the agent chose this operation (1-2 sentences)
- `rows_affected: int` — computed after apply
- `reversible: bool` — whether undo is supported

### What the agent actually outputs

The LLM's response to a refinement command should be a structured JSON array of operations, not natural language:

```json
[
  {
    "type": "AddColumn",
    "table": "transactions",
    "name": "customer_lifetime_value",
    "type": "float",
    "description": "Total spend by this customer across all transactions",
    "constraints": {
      "min": 0,
      "distribution": "log_normal",
      "correlated_with": [
        {"column": "purchase_frequency", "coefficient": 0.72},
        {"column": "avg_order_value", "coefficient": 0.68}
      ]
    },
    "agent_reasoning": "CLV is derived from purchase frequency and order value; log-normal distribution reflects natural spend clustering."
  }
]
```

This is the LangGraph tool call that replaces the current free-form generation. The agent's job is to translate user intent into this vocabulary reliably.

---

## The Dataset Session

The dataset session is the in-memory object that persists across the entire conversation. It is the equivalent of an open file in Cursor. It does not exist yet in the codebase.

```
DatasetSession {
  session_id: str
  created_at: datetime
  
  # What the user is building (updated by the agent each turn)
  intent_summary: str      # e.g. "E-commerce platform: customers, orders, seasonal fraud patterns"
  
  # The live dataset
  tables: {
    [table_name]: TableState {
      schema: ColumnDef[]
      row_count: int
      stats: {
        [column_name]: ColumnStats {
          dtype: str
          min: any
          max: any
          mean: float | None
          stddev: float | None
          cardinality: int
          null_rate: float
          sample_values: any[]   # 10-20 representative values
          distribution_hint: str  # "normal", "log_normal", "categorical", "datetime", etc.
        }
      }
      sample_rows: Row[]          # 50 rows, refreshed after each operation
    }
  }
  
  relationships: ForeignKey[]
  
  # Operation history (the undo stack)
  operations_log: Operation[]
  
  # User-stated invariants (preserved across operations)
  constraints: [
    "fraud rate approximately 2%",
    "seasonal spike in December",
    "customer age skews 25-45"
  ]
  
  # Artifact references (actual data lives here, not in session)
  artifact_id: str           # pointer to file storage
  artifact_version: int      # incremented on each apply
}
```

### What the agent sees per turn

The agent does NOT see the full session object. It receives a condensed context:

```
System prompt:
  You are a data refinement agent. You output structured operations.
  Available operation types: [vocabulary]
  
Context (injected per turn):
  Intent: {session.intent_summary}
  Tables: {schema_summary}          # column names + types only
  Statistics: {stats_summary}       # min/max/mean/cardinality per column
  Sample rows: {5-10 rows}
  Relationships: {fk_list}
  Constraints: {session.constraints}
  Last 5 operations: {recent_ops}
  
User message: {current_turn}
```

This context fits in a single request. The agent never needs the full row data.

---

## The Feedback Loop

This is the architectural path from user command to rendered change. Currently the app has SSE streaming for job progress. The loop needs to be extended to stream **operations**, not just progress percentages.

```
User types refinement command
        │
        ▼
POST /v1/session/{session_id}/refine
        │
        ▼
Backend: build agent context from DatasetSession
        │
        ▼
LangGraph agent: translate command → Operation[]
        │
        ▼
Backend: validate operations (schema check, constraint check)
        │
        ▼
Backend: apply operations to dataset (generate new column values / rows)
        │
        ▼
Backend: update DatasetSession (stats, sample rows, operation log)
        │
        ▼
SSE stream: emit one event per operation as it completes
  {
    "type": "operation_applied",
    "operation": { ... },
    "diff": {
      "columns_added": ["customer_lifetime_value"],
      "rows_modified": 10000,
      "stats_delta": { "customer_lifetime_value": { ... } }
    }
  }
        │
        ▼
Frontend: render diff
  - New/changed columns highlighted in spreadsheet view
  - Operation card appears in the timeline (left or right panel)
  - Accept / Undo button per operation
        │
        ▼
User accepts or modifies
```

The key property: **the user sees what changed, not just that something happened**. Each operation card shows: what the agent did, why, how many rows were affected, and a one-click undo.

---

## Current Architecture Gap

The prototype generates complete datasets from scratch on each request. Here is the honest map of what exists and what is missing.

### Exists

| Component | Status | Notes |
|---|---|---|
| LangGraph agent (schema inference) | Working | Generates schema from prompt |
| Data generation (Faker-based) | Working | Multi-table with FK integrity |
| SSE streaming | Working | Streams progress % and log messages |
| Conversation memory (MemorySaver) | Partial | Thread ID persisted, but stateless between requests |
| FastAPI backend | Working | Full REST + SSE |
| Next.js frontend | Working | Chat, jobs, schema editor, downloads views |

### Missing

| Component | Required for moat | Effort |
|---|---|---|
| `Operation` model (typed mutations) | Yes — core | Medium |
| `DatasetSession` object | Yes — core | Medium |
| Agent context builder (schema + stats) | Yes — core | Medium |
| Refinement agent (command → operations) | Yes — core | High |
| Statistical coherence on `AddColumn` | Yes — core | High |
| SSE operation events (not just progress) | Yes — core | Small |
| Spreadsheet / data grid UI | Yes — the visible moat | High |
| Operation timeline / diff view | Yes — the Cursor moment | High |
| Undo/redo on operations | Yes | Medium |
| Session persistence (Redis/DB) | Yes — for durability | Small |
| `ColumnStats` computation on apply | Yes — feeds agent context | Medium |

---

## Build Sequence

Order is constrained by data dependencies. Nothing in the UI can be built until the backend operation model exists, because the UI needs to know the shape of the events it will receive.

### Step 1 — Define the data model (no code changes yet)
Finalise the `Operation` type vocabulary and the `DatasetSession` schema as Pydantic models. This is the contract everything else depends on. Get this right before building anything else.

**Output:** `backend/app/models/session.py`, `backend/app/models/operations.py`

### Step 2 — Build the session manager
A service that stores and retrieves `DatasetSession` objects (in-memory for now, Redis later). Exposes `create`, `get`, `apply_operation`, `undo`, `get_agent_context`.

**Output:** `backend/app/services/session.py`

### Step 3 — Extend SSE to emit operation events
Add a new event type `operation_applied` to the SSE stream. The frontend does not need to change yet — this is an additive change.

### Step 4 — Build the refinement agent
A new LangGraph agent whose job is: given an agent context (schema + stats + constraints + user command) → output `Operation[]`. Start with a subset of the vocabulary: `AddColumn`, `SetDistribution`, `InjectOutliers`, `ExpandRows`. Validate that the LLM reliably outputs well-formed operations.

**Output:** `backend/app/agents/refinement_agent.py`

### Step 5 — Build the statistical coherence engine
When `AddColumn` is applied, the value generation must be aware of existing column stats. This is the hardest step. Start simple: support correlation with one existing column (Pearson). Extend to multi-column later.

**Output:** `backend/app/services/generation/coherent.py`

### Step 6 — Build the data grid UI
A spreadsheet-style view that renders the current session's tables. Must support: column highlighting for newly added/modified columns, virtual scrolling for large row counts (render 200 rows, not all rows), column stats panel (click column → see distribution).

**Output:** `frontend/src/components/views/DataView.tsx`

### Step 7 — Build the operation timeline
A side panel (or bottom panel) that shows the operation log as cards. Each card: operation type, table/column affected, rows changed, agent reasoning, undo button. This is the most visible part of the moat.

**Output:** `frontend/src/components/OperationTimeline.tsx`

### Step 8 — Wire it together
New API endpoint `POST /v1/session/{id}/refine` that takes a natural language command and streams operation events back. Frontend chat sends refinement commands here instead of the generation endpoint.

---

## What Makes This Defensible

Once the operation model, session, and UI exist together, the product has a property that is difficult to replicate quickly:

**The dataset is a first-class artifact with a history.** Not a file that was exported once. A designed thing, with intent encoded in the session, operations that can be replayed, constraints that are preserved. Users will build mental models around this — the same way developers think in terms of commits, not file saves.

A competitor building this from scratch must solve the statistical coherence problem (hard), the operation vocabulary problem (medium, but requires domain expertise), and the UX problem (lots of iteration). They can use the same LLM. The work is in the layer below the LLM.

The June 2026 deadline is achievable if scope is locked to: steps 1–8 above, single-user, one active session at a time, no cross-dataset FK integrity (deferred), no undo beyond the last 10 operations. Everything else is v1.1.

---

## What Is Explicitly Out of Scope for MVP

- Cross-dataset referential integrity (multiple sessions joined)
- Collaborative editing (multiple users on one session)
- Undo history beyond 10 operations
- SDV-based statistical replication (the `NotImplementedError` routes)
- Scheduled / recurring generation
- Fine-grained RBAC / multi-tenant auth
- The document generation features (invoices, PDFs) — useful, not the moat
