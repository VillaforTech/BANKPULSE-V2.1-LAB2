CREATE USER events_owner WITH PASSWORD 'events_local';
CREATE USER split_owner WITH PASSWORD 'split_local';
CREATE SCHEMA IF NOT EXISTS events AUTHORIZATION events_owner;
CREATE SCHEMA IF NOT EXISTS social_split AUTHORIZATION split_owner;
GRANT CONNECT ON DATABASE bankpulse_domains TO events_owner, split_owner;
GRANT USAGE, CREATE ON SCHEMA events TO events_owner;
GRANT USAGE, CREATE ON SCHEMA social_split TO split_owner;
