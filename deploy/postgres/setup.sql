-- MeritLens on PostgreSQL: one database, two roles.
--
--   meritlens_app        everything the app needs, EXCEPT changing or deleting audit events
--   meritlens_promotion  the promotion code's role: everything except the feedback tables and the
--                        equality-monitoring data, so the database itself keeps feedback away from the model
--
-- Run it as a superuser, in two steps (see README.md in this folder):
--   1. psql -v app_password="'...'" -v promotion_password="'...'" -f setup.sql          (before the first start)
--   2. start the app once, so it creates its tables, then:
--      psql -d meritlens -f grants.sql

CREATE ROLE meritlens_app LOGIN PASSWORD :app_password;
CREATE ROLE meritlens_promotion LOGIN PASSWORD :promotion_password;
CREATE DATABASE meritlens OWNER meritlens_app;
