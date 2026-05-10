#!/bin/bash
/opt/mssql/bin/sqlservr &
PID=$!

echo "Waiting for SQL Server..."
for i in {1..30}; do
    /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C -Q "SELECT 1" &>/dev/null
    if [ $? -eq 0 ]; then
        echo "SQL Server is ready. Running init.sql..."
        /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C -i /init.sql
        echo "Done!"
        break
    fi
    echo "Attempt $i/30..."
    sleep 2
done

wait $PID