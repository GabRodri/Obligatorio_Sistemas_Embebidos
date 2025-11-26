import sqlite3
from datetime import datetime


class Database:
    def __init__(self, db_name='Database'):
        self.db_name = db_name if db_name.endswith('.db') else db_name + '.db'
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Tabla de Funcionarios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS funcionarios (
                identificacion TEXT PRIMARY KEY,
                nombre TEXT NOT NULL
            )
        ''')

        # Tabla de Eventos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                identificacion TEXT NOT NULL,
                fecha_hora TEXT NOT NULL,
                autorizado INTEGER NOT NULL,
                canal TEXT NOT NULL,
                operacion TEXT NOT NULL,
                FOREIGN KEY (identificacion) REFERENCES funcionarios (identificacion)
            )
        ''')

        conn.commit()
        conn.close()

    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        # Optimizaciones para Raspberry Pi
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = -2000")
        return conn


# Funciones para Funcionarios
def agregar_funcionario(identificacion, nombre):
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            'INSERT INTO funcionarios (identificacion, nombre) VALUES (?, ?)',
            (identificacion, nombre)
        )
        conn.commit()
        return True, "Funcionario agregado correctamente"
    except sqlite3.IntegrityError:
        return False, "Error: La identificación ya existe"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        conn.close()


def obtener_funcionarios():
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM funcionarios ORDER BY nombre')
    funcionarios = cursor.fetchall()
    conn.close()

    return funcionarios


def obtener_funcionario_por_id(identificacion):
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM funcionarios WHERE identificacion = ?', (identificacion,))
    funcionario = cursor.fetchone()
    conn.close()

    return funcionario


def modificar_funcionario(identificacion, nuevo_nombre):
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            'UPDATE funcionarios SET nombre = ? WHERE identificacion = ?',
            (nuevo_nombre, identificacion)
        )
        conn.commit()
        affected = cursor.rowcount
        conn.close()

        if affected > 0:
            return True, "Funcionario modificado correctamente"
        else:
            return False, "Error: No se encontró el funcionario"
    except Exception as e:
        return False, f"Error: {str(e)}"


def eliminar_funcionario(identificacion):
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        # Primero eliminamos los eventos asociados al funcionario
        cursor.execute('DELETE FROM eventos WHERE identificacion = ?', (identificacion,))
        # Luego eliminamos el funcionario
        cursor.execute('DELETE FROM funcionarios WHERE identificacion = ?', (identificacion,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()

        if affected > 0:
            return True, "Funcionario eliminado correctamente"
        else:
            return False, "Error: No se encontró el funcionario"
    except Exception as e:
        return False, f"Error: {str(e)}"


# Funciones para Eventos
def agregar_evento(identificacion, autorizado, operacion, canal):
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    fecha_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        cursor.execute(
            'INSERT INTO eventos (identificacion, fecha_hora, autorizado, operacion, canal) VALUES (?, ?, ?, ?, ?)',
            (identificacion, fecha_hora, autorizado, operacion, canal)
        )
        conn.commit()
        conn.close()
        return True, "Evento registrado correctamente"
    except Exception as e:
        return False, f"Error: {str(e)}"


def obtener_eventos(limite=50):
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT e.*, f.nombre 
        FROM eventos e 
        LEFT JOIN funcionarios f ON e.identificacion = f.identificacion
        ORDER BY e.fecha_hora DESC
        LIMIT ?
    ''', (limite,))
    eventos = cursor.fetchall()
    conn.close()

    return eventos


def consultar_eventos_por_fecha(fecha_inicio, fecha_fin):
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    # Convertir las fechas para incluir todo el día
    fecha_inicio_completa = f"{fecha_inicio} 00:00:00"
    fecha_fin_completa = f"{fecha_fin} 23:59:59"

    cursor.execute('''
        SELECT e.*, f.nombre 
        FROM eventos e 
        LEFT JOIN funcionarios f ON e.identificacion = f.identificacion
        WHERE e.fecha_hora BETWEEN ? AND ?
        ORDER BY e.fecha_hora DESC
    ''', (fecha_inicio_completa, fecha_fin_completa))

    eventos = cursor.fetchall()
    conn.close()

    return eventos


def obtener_estadisticas():
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    # Total de eventos
    cursor.execute('SELECT COUNT(*) FROM eventos')
    total_eventos = cursor.fetchone()[0]

    # Eventos autorizados vs no autorizados
    cursor.execute('SELECT autorizado, COUNT(*) FROM eventos GROUP BY autorizado')
    auth_stats = cursor.fetchall()

    # Eventos por canal
    cursor.execute('SELECT canal, COUNT(*) FROM eventos GROUP BY canal')
    canal_stats = cursor.fetchall()

    # Total de funcionarios
    cursor.execute('SELECT COUNT(*) FROM funcionarios')
    total_funcionarios = cursor.fetchone()[0]

    conn.close()

    return {
        'total_eventos': total_eventos,
        'auth_stats': dict(auth_stats),
        'canal_stats': dict(canal_stats),
        'total_funcionarios': total_funcionarios
    }