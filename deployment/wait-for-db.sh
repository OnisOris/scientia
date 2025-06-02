#!/bin/s
#!/bin/sh

set -e

host="$1"
shift

until PGPASSWORD=$DB_PASS psql -h "$host" -U "$DB_USER" -d "$DB_NAME" -c '\q'; do
  >&2 echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

>&2 echo "PostgreSQL is up - executing command"
exec "$@"

