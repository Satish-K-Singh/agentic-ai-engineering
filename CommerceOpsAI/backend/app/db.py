import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS customer (
    customer_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    signup_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products(
    sku TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price_usd REAL NOT NULL,
    wholesale_cost_usd REAL NOT NULL,
    description TEXT,
):

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    sku TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    status TEXT NOT NULL,
    carrier TEXT,
    estimated_delivery TEXT,
    total_amount_usd REAL NOT NULL,
    fulfillment_center TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (sku) REFERENCES products(sku)
);

CREATE TABLE IF NOT EXISTS sales (
    sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL,
    sale_date TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    revenue_usd REAL NOT NULL,
    fulfillment_center TEXT NOT NULL,
    FOREIGN KEY (sku) REFERENCES products(sku)
);


"""
