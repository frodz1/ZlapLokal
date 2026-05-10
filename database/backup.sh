#!/bin/bash

BACKUP_DIR="/var/opt/mssql/backups"
CUSTOM_NAME=${1:-$(date +"%Y%m%d_%H%M%S")}
DB_BACKUP_FILE="$BACKUP_DIR/ZlapLokalDB_Full_$CUSTOM_NAME.bak"
LOG_BACKUP_FILE="$BACKUP_DIR/ZlapLokalDB_Log_$CUSTOM_NAME.trn"

echo "Starting the backup process..."

/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C -Q "ALTER DATABASE ZlapLokalDB SET RECOVERY FULL;" &>/dev/null

/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C -Q "BACKUP DATABASE ZlapLokalDB TO DISK = '$DB_BACKUP_FILE' WITH FORMAT, MEDIANAME = 'ZlapLokalDB_Data', NAME = 'Full Backup of ZlapLokalDB';"

/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C -Q "BACKUP LOG ZlapLokalDB TO DISK = '$LOG_BACKUP_FILE';"

echo "Done! Files saved in: $BACKUP_DIR"
echo "Database: ZlapLokalDB_Full_$CUSTOM_NAME.bak"
