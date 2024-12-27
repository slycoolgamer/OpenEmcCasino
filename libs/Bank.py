import os
import sqlite3

# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # Parent directory of 'libs'
DB_PATH = os.path.join(BASE_DIR, 'store', 'users.db')

# Initialize the database if not exists
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                userid TEXT PRIMARY KEY,
                balance REAL DEFAULT 0.0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                balance REAL DEFAULT 0.0
            )
        ''')
        # Initialize the bank balance if not exists
        cursor.execute('''
            INSERT INTO bank (balance)
            SELECT 0.0 WHERE NOT EXISTS (SELECT 1 FROM bank)
        ''')
        conn.commit()

# Get user balance
def get_user_balance(userid):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM users WHERE userid = ?', (userid,))
        result = cursor.fetchone()
        if result is None:
            cursor.execute('INSERT INTO users (userid) VALUES (?)', (userid,))
            conn.commit()
            return 0.0
        return result[0]

# Get bank balance
def get_bank_balance():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM bank')
        result = cursor.fetchone()
        return result[0] if result else 0.0    

# Update user balance
def change_balance(userid, amount):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        current_balance = get_user_balance(userid)
        new_balance = current_balance + amount
        cursor.execute('UPDATE users SET balance = ? WHERE userid = ?', (new_balance, userid))
        conn.commit()
        return new_balance

# Transfer between users
def transfer(sender, receiver, amount):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        sender_balance = get_user_balance(sender)
        if sender_balance < amount:
            raise ValueError(f"{sender} has insufficient funds.")
        receiver_balance = get_user_balance(receiver)
        cursor.execute('UPDATE users SET balance = ? WHERE userid = ?', (sender_balance - amount, sender))
        cursor.execute('UPDATE users SET balance = ? WHERE userid = ?', (receiver_balance + amount, receiver))
        conn.commit()
        return sender_balance - amount, receiver_balance + amount

# Transfer to/from bank
def bank_transfer(userid, amount):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        current_balance = get_user_balance(userid)
        cursor.execute('SELECT balance FROM bank')
        bank_balance = cursor.fetchone()[0]

        # Moving money from user to bank
        if amount < 0 and current_balance >= abs(amount):
            cursor.execute('UPDATE users SET balance = ? WHERE userid = ?', (current_balance + amount, userid))
            cursor.execute('UPDATE bank SET balance = ?', (bank_balance - amount,))
        # Moving money from bank to user
        elif amount > 0 and bank_balance >= amount:
            cursor.execute('UPDATE users SET balance = ? WHERE userid = ?', (current_balance + amount, userid))
            cursor.execute('UPDATE bank SET balance = ?', (bank_balance - amount,))
        else:
            raise ValueError("Insufficient funds in bank or user account.")
        conn.commit()
        return current_balance + amount, bank_balance - amount

# Ensure database is ready
init_db()
