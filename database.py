import sqlite3

def crear_bd():
    conn = sqlite3.connect('prestamos.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dni TEXT UNIQUE,
            nombres TEXT,
            apellidos TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prestamos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            monto REAL,
            cuotas INTEGER,
            fecha TEXT,
            FOREIGN KEY(cliente_id) REFERENCES clientes(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cuotas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prestamo_id INTEGER,
            numero INTEGER,
            monto REAL,
            pagado INTEGER DEFAULT 0,
            FOREIGN KEY(prestamo_id) REFERENCES prestamos(id)
        )
    ''')

    # Usuario admin por defecto
    cursor.execute("INSERT OR IGNORE INTO usuarios (username, password) VALUES (?, ?)", ('admin', 'admin123'))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    crear_bd()
