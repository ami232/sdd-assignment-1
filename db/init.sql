-- creates one database and one user per service like on Azure SQL, and checks before every step so it is safe to run on every start

-- contained databases let a user sign in straight to one database, which is also how users work on Azure SQL
EXEC sp_configure 'contained database authentication', 1;
RECONFIGURE;
GO

IF DB_ID('library_db') IS NULL
    CREATE DATABASE library_db CONTAINMENT = PARTIAL;
GO
IF DB_ID('group_db') IS NULL
    CREATE DATABASE group_db CONTAINMENT = PARTIAL;
GO

-- a contained user exists only inside its own database, so library_user cannot even sign in to group_db
USE library_db;
GO
IF USER_ID('library_user') IS NULL
    CREATE USER library_user WITH PASSWORD = '$(LIBRARY_DB_PASSWORD)';
ELSE
    ALTER USER library_user WITH PASSWORD = '$(LIBRARY_DB_PASSWORD)';
-- these three roles let the service read and write its data and run its own migrations, and nothing more
ALTER ROLE db_ddladmin ADD MEMBER library_user;
ALTER ROLE db_datareader ADD MEMBER library_user;
ALTER ROLE db_datawriter ADD MEMBER library_user;
GO

USE group_db;
GO
IF USER_ID('group_user') IS NULL
    CREATE USER group_user WITH PASSWORD = '$(GROUP_DB_PASSWORD)';
ELSE
    ALTER USER group_user WITH PASSWORD = '$(GROUP_DB_PASSWORD)';
ALTER ROLE db_ddladmin ADD MEMBER group_user;
ALTER ROLE db_datareader ADD MEMBER group_user;
ALTER ROLE db_datawriter ADD MEMBER group_user;
GO