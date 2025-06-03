#!/bin/s#!/bin/sh

set -e

echo "Waiting for PostgreSQL..."
while ! nc -z db 5432; do
  sleep 1
done

echo "PostgreSQL is up - starting application"
exec scientia-app
