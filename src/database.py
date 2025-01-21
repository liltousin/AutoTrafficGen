import psycopg2

# Database configuration
DB_CONFIG = {
    "dbname": "autotraficgen",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": 5432,
}

# SQL queries to set up tables
CREATE_TABLES_QUERIES = [
    """
    CREATE TABLE IF NOT EXISTS proxies (
        id SERIAL PRIMARY KEY,
        ip VARCHAR(45) NOT NULL,
        port INTEGER NOT NULL,
        protocol VARCHAR(10) NOT NULL,
        real_ip VARCHAR(45),
        score FLOAT NOT NULL,
        good_count INTEGER DEFAULT 0,
        bad_count INTEGER DEFAULT 0,
        response FLOAT DEFAULT 0,
        used_count INTEGER DEFAULT 0,
        last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(ip, port, protocol)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS accounts (
        id SERIAL PRIMARY KEY,
        username VARCHAR(255) NOT NULL,
        password VARCHAR(255) NOT NULL,
        proxy_id INTEGER REFERENCES proxies(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(20) DEFAULT 'active'
    );
    """,
]


def connect_to_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("Database connection established.")
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None


def setup_database():
    conn = connect_to_db()
    if conn is None:
        return

    try:
        cur = conn.cursor()
        for query in CREATE_TABLES_QUERIES:
            cur.execute(query)
        conn.commit()
        print("Database tables created successfully.")
    except Exception as e:
        print(f"Error setting up the database: {e}")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    setup_database()
