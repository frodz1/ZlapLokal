#!/bin/bash

until printf "" 2>>/dev/null >/dev/tcp/db/1433; do
    sleep 2
done

python manage.py runserver 0.0.0.0:8000
