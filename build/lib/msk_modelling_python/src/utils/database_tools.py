
import sqlite3
import os

def create_default_database():
    # Get the directory path of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Specify the relative path for the database file
    database_path = os.path.join(script_dir, '..', 'database', 'default.db')

    print(database_path)

    # Connect to the database
    conn = sqlite3.connect(database_path)
    # Create a cursor object to execute SQL statements
    cursor = conn.cursor()

    # Execute SQL statements to create tables, insert data, etc.
    # ...

    # Commit the changes and close the connection
    conn.commit()
    conn.close()





