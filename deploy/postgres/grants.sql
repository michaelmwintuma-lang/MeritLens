-- Run after the app has started once and created its tables:   psql -d meritlens -f grants.sql
-- (as a superuser or as meritlens_app). Safe to run again after an update adds tables.

-- The promotion code: read and write every table it needs...
GRANT USAGE ON SCHEMA public TO meritlens_promotion;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO meritlens_promotion;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO meritlens_promotion;

-- ...but never the employees' feedback, nor the equality-monitoring data (gender, age band, education).
-- A query from the promotion code that touches them fails with "permission denied".
REVOKE ALL ON explanation_ratings, correction_requests, equality_monitoring FROM meritlens_promotion;

-- The audit trail is append-only for everyone the app connects as: events can be added and read, never changed
-- or deleted. (Its hash chain would show a change made by a superuser; see /api/governance/audit/verify.)
REVOKE UPDATE, DELETE, TRUNCATE ON audit_events FROM meritlens_promotion;
REVOKE UPDATE, DELETE, TRUNCATE ON audit_events FROM meritlens_app;
