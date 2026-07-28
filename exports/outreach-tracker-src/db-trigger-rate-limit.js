"use strict";

/**
 * db-trigger-rate-limit.js
 *
 * Factory that returns the dbTriggerRateLimit Express middleware.
 * Accepts a `queryFn` argument so tests can inject a stub without touching
 * the DB, while production passes in the real `query` from ./db.
 */

const TRIGGER_RL_MAX = 3;
const TRIGGER_RL_WINDOW_MS = 60 * 60 * 1000; // 1 hour
const TRIGGER_RL_MESSAGE =
  "Too many backup requests. Please wait before trying again.";
const TRIGGER_RL_DB_ERROR_MESSAGE =
  "Backup service temporarily unavailable. Please try again shortly.";

/**
 * @param {Function} queryFn  — async (sql, params) => { rows }
 * @returns Express middleware
 */
function makeTriggerRateLimit(queryFn) {
  return async function dbTriggerRateLimit(req, res, next) {
    const ip = req.ip;
    try {
      // Atomic upsert: reset the bucket when the window has expired, else increment.
      const { rows } = await queryFn(
        `INSERT INTO trigger_rate_limit (ip, count, first_at)
         VALUES ($1, 1, NOW())
         ON CONFLICT (ip) DO UPDATE SET
           count    = CASE
                        WHEN trigger_rate_limit.first_at < NOW() - ($2 * INTERVAL '1 millisecond')
                        THEN 1
                        ELSE trigger_rate_limit.count + 1
                      END,
           first_at = CASE
                        WHEN trigger_rate_limit.first_at < NOW() - ($2 * INTERVAL '1 millisecond')
                        THEN NOW()
                        ELSE trigger_rate_limit.first_at
                      END
         RETURNING count, EXTRACT(EPOCH FROM first_at)::BIGINT * 1000 AS first_ms`,
        [ip, TRIGGER_RL_WINDOW_MS]
      );
      const { count, first_ms } = rows[0];
      if (count > TRIGGER_RL_MAX) {
        const waitSec = Math.ceil(
          (Number(first_ms) + TRIGGER_RL_WINDOW_MS - Date.now()) / 1000
        );
        res.setHeader("Retry-After", String(Math.max(waitSec, 1)));
        return res.status(429).json({ error: TRIGGER_RL_MESSAGE });
      }
      return next();
    } catch (e) {
      // Fail closed: if the rate-limit table is unreachable we cannot enforce
      // the cap, so reject the request rather than silently allow it through.
      console.error("dbTriggerRateLimit DB error:", e);
      return res.status(503).json({ error: TRIGGER_RL_DB_ERROR_MESSAGE });
    }
  };
}

module.exports = {
  makeTriggerRateLimit,
  TRIGGER_RL_MAX,
  TRIGGER_RL_WINDOW_MS,
  TRIGGER_RL_MESSAGE,
  TRIGGER_RL_DB_ERROR_MESSAGE,
};
