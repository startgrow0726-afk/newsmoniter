import os, psycopg2

try:
    dsn = (
        f"host={os.getenv('POSTGRES_HOST','168.107.18.155')} "
        f"port={os.getenv('POSTGRES_PORT','5432')} "
        f"dbname={os.getenv('POSTGRES_DB','newsmon')} "
        f"user={os.getenv('POSTGRES_USER','newsmon')} "
        f"password={os.getenv('POSTGRES_PASSWORD','change_me_strong')}"
    )
    # The script is in /app in the container, so schema.sql is at ./schema.sql
    with open('./schema.sql', 'r') as f:
        schema_sql = f.read()
    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
    print("Database schema applied successfully.")
except Exception as e:
    print(f"An error occurred: {e}")
