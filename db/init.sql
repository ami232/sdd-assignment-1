-- Local setup for SQL Server: one database and one login per service.
-- The db-init compose job runs this on every `docker compose up`, so it
-- only creates what is missing. The tables are not created here: each
-- service creates its own with its migrations (services/<name>/migrations).
--
-- The passwords are sqlcmd variables, filled in from the environment
-- variables TRIPS_DB_PASSWORD and ROOMS_DB_PASSWORD (set in .env), so they
-- are never written in this file.
--
-- Each login is a user in its own database only. SQL Server gives a login
-- no access to a database where it has no user, so trips_app cannot read
-- the rooms database and rooms_app cannot read the trips database.
-- db_owner lets each service create and change its own tables.

IF DB_ID('trips') IS NULL
    CREATE DATABASE trips;
GO
IF DB_ID('rooms') IS NULL
    CREATE DATABASE rooms;
GO

IF SUSER_ID('trips_app') IS NULL
    CREATE LOGIN trips_app WITH PASSWORD = '$(TRIPS_DB_PASSWORD)';
GO
IF SUSER_ID('rooms_app') IS NULL
    CREATE LOGIN rooms_app WITH PASSWORD = '$(ROOMS_DB_PASSWORD)';
GO

USE trips;
IF USER_ID('trips_app') IS NULL
BEGIN
    CREATE USER trips_app FOR LOGIN trips_app;
    ALTER ROLE db_owner ADD MEMBER trips_app;
END
GO

USE rooms;
IF USER_ID('rooms_app') IS NULL
BEGIN
    CREATE USER rooms_app FOR LOGIN rooms_app;
    ALTER ROLE db_owner ADD MEMBER rooms_app;
END
GO
