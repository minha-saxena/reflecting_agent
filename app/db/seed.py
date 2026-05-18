import sqlite3
from typing import Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)

_conn: Optional[sqlite3.Connection] = None


def get_connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = _init_db()
    return _conn


def _init_db() -> sqlite3.Connection:
    logger.info("Initialising in-memory SQLite database...")
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE customers (
        id          INTEGER PRIMARY KEY,
        name        TEXT    NOT NULL,
        email       TEXT    NOT NULL,
        city        TEXT,
        joined_date TEXT
    );

    CREATE TABLE products (
        id       INTEGER PRIMARY KEY,
        name     TEXT    NOT NULL,
        category TEXT,
        price    REAL    NOT NULL,
        stock    INTEGER DEFAULT 0
    );

    CREATE TABLE orders (
        id          INTEGER PRIMARY KEY,
        customer_id INTEGER NOT NULL,
        product_id  INTEGER NOT NULL,
        quantity    INTEGER NOT NULL DEFAULT 1,
        order_date  TEXT,
        status      TEXT    CHECK(status IN ('completed','pending','cancelled')),
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (product_id)  REFERENCES products(id)
    );
    """)

    cursor.executemany(
        "INSERT INTO customers VALUES (?,?,?,?,?)",
        [
            (1, "Alice Johnson", "alice@example.com",  "New York",     "2022-01-15"),
            (2, "Bob Smith",     "bob@example.com",    "Los Angeles",  "2022-03-20"),
            (3, "Carol White",   "carol@example.com",  "Chicago",      "2021-11-08"),
            (4, "David Lee",     "david@example.com",  "Houston",      "2023-02-14"),
            (5, "Eva Brown",     "eva@example.com",    "Phoenix",      "2022-07-30"),
            (6, "Frank Davis",   "frank@example.com",  "San Antonio",  "2021-05-19"),
            (7, "Grace Wilson",  "grace@example.com",  "New York",     "2023-06-01"),
            (8, "Henry Moore",   "henry@example.com",  "Los Angeles",  "2022-09-12"),
        ],
    )

    cursor.executemany(
        "INSERT INTO products VALUES (?,?,?,?,?)",
        [
            (1,  "Laptop Pro 15",       "Electronics", 1299.99, 45),
            (2,  "Wireless Mouse",      "Electronics",   29.99, 200),
            (3,  "Mechanical Keyboard", "Electronics",   89.99, 150),
            (4,  "USB-C Hub",           "Electronics",   49.99, 300),
            (5,  "Standing Desk",       "Furniture",    599.99,  20),
            (6,  "Ergonomic Chair",     "Furniture",    449.99,  35),
            (7,  "Notebook Set",        "Stationery",    12.99, 500),
            (8,  "Ballpoint Pens",      "Stationery",     5.99, 800),
            (9,  'Monitor 27"',         "Electronics",  399.99,  60),
            (10, "Webcam HD",           "Electronics",   79.99, 120),
        ],
    )

    cursor.executemany(
        "INSERT INTO orders VALUES (?,?,?,?,?,?)",
        [
            (1,  1, 1,  1, "2024-01-10", "completed"),
            (2,  1, 2,  2, "2024-01-15", "completed"),
            (3,  2, 3,  1, "2024-01-20", "completed"),
            (4,  3, 5,  1, "2024-02-01", "completed"),
            (5,  4, 9,  2, "2024-02-10", "completed"),
            (6,  5, 6,  1, "2024-02-15", "completed"),
            (7,  2, 4,  3, "2024-02-20", "completed"),
            (8,  6, 1,  1, "2024-03-01", "completed"),
            (9,  7, 10, 2, "2024-03-05", "completed"),
            (10, 8, 7,  5, "2024-03-10", "completed"),
            (11, 1, 9,  1, "2024-03-12", "completed"),
            (12, 3, 2,  4, "2024-03-15", "completed"),
            (13, 4, 3,  2, "2024-03-18", "pending"),
            (14, 5, 8, 10, "2024-03-20", "completed"),
            (15, 6, 4,  2, "2024-03-22", "completed"),
            (16, 7, 5,  1, "2024-03-25", "cancelled"),
            (17, 2, 1,  1, "2024-03-28", "pending"),
            (18, 8, 6,  1, "2024-04-01", "completed"),
        ],
    )

    # Customers with NO orders
    cursor.executemany(
        "INSERT INTO customers VALUES (?,?,?,?,?)",
        [
            (9,  "Isla Carter", "isla@example.com", "Miami",   "2023-08-10"),
            (10, "Jack Turner", "jack@example.com", "Seattle", "2022-12-05"),
        ],
    )

    # Products NEVER ordered
    cursor.executemany(
        "INSERT INTO products VALUES (?,?,?,?,?)",
        [
            (11, "Gaming Chair X",  "Furniture",   899.99, 10),
            (12, "Smart Light Kit", "Electronics", 129.99, 75),
        ],
    )

    # Cancelled-heavy patterns
    cursor.executemany(
        "INSERT INTO orders VALUES (?,?,?,?,?,?)",
        [
            (19, 2, 2, 1, "2024-04-05", "cancelled"),
            (20, 2, 3, 2, "2024-04-06", "cancelled"),
            (21, 4, 1, 1, "2024-04-07", "cancelled"),
            (22, 4, 5, 1, "2024-04-08", "cancelled"),
            (23, 5, 6, 1, "2024-04-09", "cancelled"),
            (24, 5, 7, 3, "2024-04-10", "cancelled"),
        ],
    )

    # Same-day duplicates
    cursor.executemany(
        "INSERT INTO orders VALUES (?,?,?,?,?,?)",
        [
            (25, 1, 1, 1, "2024-04-10", "completed"),
            (26, 1, 1, 1, "2024-04-10", "completed"),
            (27, 3, 2, 2, "2024-04-10", "completed"),
        ],
    )

    # NULL order_date
    cursor.executemany(
        "INSERT INTO orders VALUES (?,?,?,?,?,?)",
        [
            (28, 6, 3, 1, None, "completed"),
            (29, 7, 4, 2, None, "pending"),
        ],
    )

    conn.commit()
    logger.info("Database seeded successfully.")
    return conn


def get_schema_info() -> str:
    return """DATABASE SCHEMA
===============

TABLE: customers
  - id          INTEGER  PRIMARY KEY
  - name        TEXT     NOT NULL          -- e.g. 'Alice Johnson', 'Bob Smith'
  - email       TEXT     NOT NULL          -- e.g. 'alice@example.com'
  - city        TEXT                       -- e.g. 'New York', 'Los Angeles', 'Chicago'
  - joined_date TEXT                       -- format: 'YYYY-MM-DD'

TABLE: products
  - id          INTEGER  PRIMARY KEY
  - name        TEXT     NOT NULL          -- e.g. 'Laptop Pro 15', 'Wireless Mouse'
  - category    TEXT                       -- ONLY: 'Electronics', 'Furniture', 'Stationery'
  - price       REAL     NOT NULL          -- unit price, e.g. 1299.99
  - stock       INTEGER  DEFAULT 0         -- units in stock

TABLE: orders
  - id          INTEGER  PRIMARY KEY
  - customer_id INTEGER  NOT NULL  REFERENCES customers(id)
  - product_id  INTEGER  NOT NULL  REFERENCES products(id)
  - quantity    INTEGER  NOT NULL  DEFAULT 1
  - order_date  TEXT               -- format: 'YYYY-MM-DD', can be NULL
  - status      TEXT               -- ONLY: 'completed', 'pending', 'cancelled'

RELATIONSHIPS
  orders.customer_id  →  customers.id
  orders.product_id   →  products.id

IMPORTANT NOTES
  - Revenue = products.price * orders.quantity  (no price column in orders)
  - Total spend per customer: SUM(products.price * orders.quantity)
  - Filter completed orders with: WHERE orders.status = 'completed'
  - Some orders have NULL order_date — use IS NOT NULL to exclude them
  - Some customers have NO orders (ids 9, 10)
  - Some products have NEVER been ordered (ids 11, 12)
  - category is on the products table, NOT on orders
  - Use products.category, NOT orders.category (orders has no category column)
"""