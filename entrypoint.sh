#!/bin/bash
/opt/mssql/bin/sqlservr &
PID=$!

echo "Czekam na SQL Server..."
for i in {1..30}; do
    /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -Q "SELECT 1" -No &>/dev/null
    if [ $? -eq 0 ]; then
        echo "SQL Server gotowy. Uruchamiam init.sql..."
        /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -i /init.sql -No
        echo "Gotowe!"
        break
    fi
    echo "Próba $i/30..."
    sleep 2
done

wait $PID
