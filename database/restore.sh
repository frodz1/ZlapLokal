#!/bin/bash

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Error: You must provide the path to the backup file (.bak)!"
    echo "Usage: /restore.sh /var/opt/mssql/backups/filename.bak"
    exit 1
fi

echo "Restoring database from file: $BACKUP_FILE ..."

/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C -Q "ALTER DATABASE ZlapLokalDB SET SINGLE_USER WITH ROLLBACK IMMEDIATE;" &>/dev/null

/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C -Q "RESTORE DATABASE ZlapLokalDB FROM DISK = '$BACKUP_FILE' WITH REPLACE;"

/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C -Q "ALTER DATABASE ZlapLokalDB SET MULTI_USER;" &>/dev/null

echo "Restore completed successfully!"