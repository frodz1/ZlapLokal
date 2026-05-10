FROM mcr.microsoft.com/mssql/server:2022-latest

USER root


RUN apt-get update && \
    apt-get install -y cron sudo && \
    rm -rf /var/lib/apt/lists/*

# Copy scripts
COPY backup.sh /usr/local/bin/backup.sh
COPY init.sql /init.sql
COPY entrypoint.sh /entrypoint.sh


RUN chmod +x /usr/local/bin/backup.sh && \
    chmod +x /entrypoint.sh


RUN echo "0 3 * * * root /usr/local/bin/backup.sh automated >> /var/log/cron.log 2>&1" > /etc/cron.d/db-backup
RUN chmod 0644 /etc/cron.d/db-backup


USER mssql

ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]