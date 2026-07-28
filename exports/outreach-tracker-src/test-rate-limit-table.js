/**
 * test-rate-limit-table.js
 *
 * Confirms that the trigger_rate_limit table exists in the connected Postgres
 * database with the correct columns (ip, count, first_at).
 *
 * The DB-backed triggerLimiter in server.js reads and writes this table so the
 * 3-per-hour cap survives process restarts.  If the table is absent the
 * middleware fails open — no rate limit is enforced at all.  This check is the
 * deploy gate that makes that failure visible instead of silent.
 *
 * Usage:
 *   DATABASE_URL=postgres://... node test-rate-limit-table.js
 *
 * Exit codes: 0 = table present and schema correct, 1 = missing or wrong.
 */

"use strict";

const { Pool } = require("pg");

if (!process.env.DATABASE_URL) {
  console.error("ERROR: DATABASE_URL is not set.");
  process.exit(1);
}

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

function assert(condition, message) {
  if (!condition) {
    console.error(`  FAIL: ${message}`);
    process.exitCode = 1;
  } else {
    console.log(`  PASS: ${message}`);
  }
}

async function run() {
  console.log("=== trigger_rate_limit table existence check ===\n");

  const { rows } = await pool.query(`
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name   = 'trigger_rate_limit'
    ORDER BY ordinal_position
  `);

  assert(
    rows.length > 0,
    "trigger_rate_limit table exists in the database"
  );

  if (rows.length === 0) {
    console.error(
      "\n  The table is missing.  Apply the schema:\n" +
      "    psql $DATABASE_URL < schema.sql\n" +
      "  or run the CREATE TABLE block from schema.sql manually.\n"
    );
    console.log("\n=== Done (FAILED) ===");
    return;
  }

  const cols = Object.fromEntries(rows.map((r) => [r.column_name, r]));

  assert("ip"       in cols, "column 'ip' exists");
  assert("count"    in cols, "column 'count' exists");
  assert("first_at" in cols, "column 'first_at' exists");

  if ("ip" in cols) {
    assert(
      cols.ip.data_type === "text",
      `column 'ip' has type text (got '${cols.ip.data_type}')`
    );
    assert(
      cols.ip.is_nullable === "NO",
      `column 'ip' is NOT NULL (got is_nullable='${cols.ip.is_nullable}')`
    );
  }

  if ("count" in cols) {
    assert(
      cols.count.data_type === "integer",
      `column 'count' has type integer (got '${cols.count.data_type}')`
    );
    assert(
      cols.count.is_nullable === "NO",
      `column 'count' is NOT NULL (got is_nullable='${cols.count.is_nullable}')`
    );
  }

  if ("first_at" in cols) {
    assert(
      cols.first_at.data_type === "timestamp with time zone",
      `column 'first_at' has type timestamptz (got '${cols.first_at.data_type}')`
    );
    assert(
      cols.first_at.is_nullable === "NO",
      `column 'first_at' is NOT NULL (got is_nullable='${cols.first_at.is_nullable}')`
    );
  }

  // Verify ip is the primary key
  const { rows: pkRows } = await pool.query(`
    SELECT kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
     AND tc.table_schema    = kcu.table_schema
    WHERE tc.constraint_type = 'PRIMARY KEY'
      AND tc.table_schema    = 'public'
      AND tc.table_name      = 'trigger_rate_limit'
  `);
  assert(
    pkRows.length === 1 && pkRows[0].column_name === "ip",
    `primary key is 'ip' (got [${pkRows.map((r) => r.column_name).join(", ")}])`
  );

  console.log("\n=== Done ===");
}

run()
  .catch((err) => {
    console.error("Unexpected error:", err);
    process.exitCode = 1;
  })
  .finally(() => pool.end());
