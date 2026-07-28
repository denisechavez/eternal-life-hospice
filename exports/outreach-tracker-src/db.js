const { Pool } = require("pg");

if (!process.env.DATABASE_URL) {
  console.error("DATABASE_URL is not set. The tracker needs a Postgres database.");
}

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

pool.on("error", (err) => {
  console.error("Unexpected Postgres pool error:", err);
});

async function query(text, params) {
  return pool.query(text, params);
}

module.exports = { pool, query };
