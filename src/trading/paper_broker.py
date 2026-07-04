import sqlite3
import config
from datetime import datetime


def get_connection():
    import os
    import shutil
    db_path = os.path.abspath(config.DB_PATH)
    db_dir = os.path.dirname(db_path)
    try:
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.OperationalError:
        # Fallback to writeable temp folder on Linux/macOS or Windows
        print(f"[DB] OperationalError opening {db_path}. Falling back to system temp folder.")
        tmp_db_path = "/tmp/paper_trades.db"
        if os.name == 'nt':
            import tempfile
            tmp_db_path = os.path.join(tempfile.gettempdir(), "paper_trades.db")
        
        # If the temp database does not exist, copy the pre-populated repository database
        if not os.path.exists(tmp_db_path) and os.path.exists(db_path):
            try:
                shutil.copy(db_path, tmp_db_path)
                print(f"[DB] Copied pre-populated database to {tmp_db_path}")
            except Exception as copy_err:
                print(f"[DB] Failed to copy pre-populated database: {copy_err}")
                
        conn = sqlite3.connect(tmp_db_path)
        return conn




def add_column_if_not_exists(conn, col_name, col_type):
    try:
        conn.execute(f"ALTER TABLE trades ADD COLUMN {col_name} {col_type}")
        conn.commit()
        print(f"[DB] Migration: Added column '{col_name}' to trades.")
    except sqlite3.OperationalError:
        # Column already exists
        pass


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            city TEXT,
            question TEXT,
            side TEXT,
            price REAL,
            stake REAL,
            model_probability REAL,
            rationale TEXT,
            trade_type TEXT DEFAULT 'primary'
        )
    """)
    conn.commit()
    
    # Run migrations for new analytics/LLM columns
    add_column_if_not_exists(conn, "target_date", "TEXT")
    add_column_if_not_exists(conn, "temp_threshold", "REAL")
    add_column_if_not_exists(conn, "condition", "TEXT")
    add_column_if_not_exists(conn, "actual_temp", "REAL")
    add_column_if_not_exists(conn, "resolved", "INTEGER DEFAULT 0")
    add_column_if_not_exists(conn, "pnl", "REAL DEFAULT 0.0")
    add_column_if_not_exists(conn, "llm_critique", "TEXT")
    
    conn.close()


def record_trade(city, question, side, price, stake, model_probability, rationale, 
                 trade_type="primary", target_date=None, temp_threshold=None, 
                 condition=None, llm_critique=None):
    conn = get_connection()
    conn.execute("""
        INSERT INTO trades (
            timestamp, city, question, side, price, stake, 
            model_probability, rationale, trade_type, 
            target_date, temp_threshold, condition, llm_critique
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        city,
        question,
        side,
        price,
        stake,
        model_probability,
        rationale,
        trade_type,
        target_date,
        temp_threshold,
        condition,
        llm_critique,
    ))
    conn.commit()
    conn.close()


def resolve_trade_in_db(trade_id, actual_temp, pnl):
    conn = get_connection()
    conn.execute("""
        UPDATE trades 
        SET resolved = 1, actual_temp = ?, pnl = ?
        WHERE id = ?
    """, (actual_temp, pnl, trade_id))
    conn.commit()
    conn.close()


def get_all_trades():
    conn = get_connection()
    # Self-heal: check if the 'trades' table exists. If not, run init_db()
    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
        table_exists = cursor.fetchone()
    except sqlite3.OperationalError:
        table_exists = False
        
    if not table_exists:
        conn.close()
        init_db()
        conn = get_connection()
        
    cursor = conn.execute("SELECT * FROM trades ORDER BY timestamp DESC")
    columns = [description[0] for description in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return rows
