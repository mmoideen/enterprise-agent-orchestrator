-- Initialize enterprise_agents database
-- This script runs on first container startup

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE enterprise_agents TO "user";

-- Create schemas for organization
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS governance;

-- Grant schema privileges
GRANT ALL PRIVILEGES ON SCHEMA audit TO "user";
GRANT ALL PRIVILEGES ON SCHEMA governance TO "user";
