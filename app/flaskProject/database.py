import sqlite3
from datetime import datetime
import logging
from logger_config import setup_logger
import traceback

logger = setup_logger("database", "db.log", level=logging.INFO)


class Database:
    def __init__(self, db_name='Database'):
        self.db_name = db_name if db_name.endswith('.db') else db_name + '.db'
        self.init_db()

    def init_db(self):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS funcionarios (
                    identificacion TEXT PRIMARY KEY,
                    nombre TEXT NOT NULL
                )
            ''')

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
            logger.info("Inicialización de base de datos completada")

        except Exception as e:
            logger.error(f"Error durante init_db: {e}")
            logger.error(traceback.format_exc())

        finally:
            conn.close()

    def get_connection(self):
        try:
            conn = sqlite3.connect(self.db_name)
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA cache_size = -2000")
            return conn

        except Exception as e:
            logger.error(f"Error obteniendo conexión a DB: {e}")
            logger.error(traceback.format_exc())
            raise


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
        logger.info(f"Funcionario agregado: {identificacion} - {nombre}")
        return True, "Funcionario agregado correctamente"

    except sqlite3.IntegrityError:
        logger.warning(f"Intento de duplicado de identificación: {identificacion}")
        return False, "Error: La identificación ya existe"

    except Exception as e:
        logger.error(f"Error agregando funcionario {identificacion}: {e}")
        logger.error(traceback.format_exc())
        return False, f"Error: {str(e)}"

    finally:
        conn.close()


def obtener_funcionarios():
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT * FROM funcionarios ORDER BY nombre')
        funcionarios = cursor.fetchall()
        logger.info(f"Consulta funcionarios: {len(funcionarios)} encontrados")
        return funcionarios

    except Exception as e:
        logger.error(f"Error obteniendo lista de funcionarios: {e}")
        logger.error(traceback.format_exc())
        return []

    finally:
        conn.close()


def obtener_funcionario_por_id(identificacion):
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT * FROM funcionarios WHERE identificacion = ?', (identificacion,))
        funcionario = cursor.fetchone()
        logger.info(f"Consulta funcionario {identificacion}: {'ENCONTRADO' if funcionario else 'NO ENCONTRADO'}")
        return funcionario

    except Exception as e:
        logger.error(f"Error obteniendo funcionario {identificacion}: {e}")
        logger.error(traceback.format_exc())
        return None

    finally:
        conn.close()


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

        if affected > 0:
            logger.info(f"Funcionario modificado: {identificacion} → {nuevo_nombre}")
            return True, "Funcionario modificado correctamente"
        else:
            logger.warning(f"Modificación fallida: {identificacion} no existe")
            return False, "Error: No se encontró el funcionario"

    except Exception as e:
        logger.error(f"Error modificando funcionario {identificacion}: {e}")
        logger.error(traceback.format_exc())
        return False, f"Error: {str(e)}"

    finally:
        conn.close()


def eliminar_funcionario(identificacion):
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('DELETE FROM eventos WHERE identificacion = ?', (identificacion,))
        cursor.execute('DELETE FROM funcionarios WHERE identificacion = ?', (identificacion,))
        conn.commit()
        affected = cursor.rowcount

        if affected > 0:
            logger.info(f"Funcionario eliminado: {identificacion}")
            return True, "Funcionario eliminado correctamente"
        else:
            logger.warning(f"Intento de eliminar funcionario inexistente: {identificacion}")
            return False, "Error: No se encontró el funcionario"

    except Exception as e:
        logger.error(f"Error eliminando funcionario {identificacion}: {e}")
        logger.error(traceback.format_exc())
        return False, f"Error: {str(e)}"

    finally:
        conn.close()


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
        logger.info(f"Evento agregado: ID={identificacion}, op={operacion}, canal={canal}, autorizado={autorizado}")
        return True, "Evento registrado correctamente"

    except Exception as e:
        logger.error(f"Error agregando evento para {identificacion}: {e}")
        logger.error(traceback.format_exc())
        return False, f"Error: {str(e)}"

    finally:
        conn.close()


def obtener_eventos(limite=50):
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT e.*, f.nombre 
            FROM eventos e 
            LEFT JOIN funcionarios f ON e.identificacion = f.identificacion
            ORDER BY e.fecha_hora DESC
            LIMIT ?
        ''', (limite,))
        eventos = cursor.fetchall()
        logger.info(f"Consulta últimos eventos: {len(eventos)} encontrados")
        return eventos

    except Exception as e:
        logger.error(f"Error obteniendo eventos: {e}")
        logger.error(traceback.format_exc())
        return []

    finally:
        conn.close()


def consultar_eventos_por_fecha(fecha_inicio, fecha_fin):
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    fecha_inicio_completa = f"{fecha_inicio} 00:00:00"
    fecha_fin_completa = f"{fecha_fin} 23:59:59"

    try:
        cursor.execute('''
            SELECT e.*, f.nombre 
            FROM eventos e 
            LEFT JOIN funcionarios f ON e.identificacion = f.identificacion
            WHERE e.fecha_hora BETWEEN ? AND ?
            ORDER BY e.fecha_hora DESC
        ''', (fecha_inicio_completa, fecha_fin_completa))

        eventos = cursor.fetchall()
        logger.info(f"Consulta eventos por fecha {fecha_inicio} → {fecha_fin}: {len(eventos)} encontrados")
        return eventos

    except Exception as e:
        logger.error(f"Error consultando eventos por fecha: {e}")
        logger.error(traceback.format_exc())
        return []

    finally:
        conn.close()


def obtener_estadisticas():
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT COUNT(*) FROM eventos')
        total_eventos = cursor.fetchone()[0]

        cursor.execute('SELECT autorizado, COUNT(*) FROM eventos GROUP BY autorizado')
        auth_stats = cursor.fetchall()

        cursor.execute('SELECT canal, COUNT(*) FROM eventos GROUP BY canal')
        canal_stats = cursor.fetchall()

        cursor.execute('SELECT COUNT(*) FROM funcionarios')
        total_funcionarios = cursor.fetchone()[0]

        logger.info("Estadísticas calculadas correctamente")

        return {
            'total_eventos': total_eventos,
            'auth_stats': dict(auth_stats),
            'canal_stats': dict(canal_stats),
            'total_funcionarios': total_funcionarios
        }

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        logger.error(traceback.format_exc())
        return {}

    finally:
        conn.close()


def obtener_intentos_fallidos_recientes(identificacion, minutos=1):
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT COUNT(*)
            FROM eventos
            WHERE identificacion = ?
              AND autorizado = 0 
              AND datetime(fecha_hora) >= datetime('now', ?)
        ''', (identificacion, f'-{minutos} minutes'))

        cantidad = cursor.fetchone()[0]
        logger.info(f"Intentos fallidos recientes para {identificacion}: {cantidad}")
        return cantidad

    except Exception as e:
        logger.error(f"Error al obtener intentos fallidos para {identificacion}: {e}")
        logger.error(traceback.format_exc())
        return 0

    finally:
        conn.close()
