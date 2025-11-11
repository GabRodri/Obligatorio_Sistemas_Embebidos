import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import threading
import time
import logging
from database import obtener_funcionario_por_id, agregar_evento

# ===============================
# 🔧 CONFIGURACIÓN DEL LOGGER
# ===============================
logger = logging.getLogger("RFIDReader")
logger.setLevel(logging.DEBUG)

# Formato de logs
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Handler a archivo
file_handler = logging.FileHandler("rfid_reader.log", encoding="utf-8")
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)

# Handler a consola
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# Evitar handlers duplicados si el módulo se importa más de una vez
if not logger.hasHandlers():
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# Desactivar warnings de pines
GPIO.setwarnings(False)


# ===============================
# 📡 CLASE PRINCIPAL DEL LECTOR
# ===============================

class RFIDReader:
    def __init__(self):
        self.reader = SimpleMFRC522()
        self.led_verde = 11
        self.led_rojo = 13
        self.setup_gpio()
        self.running = True

    def setup_gpio(self):
        # """Configura los pines GPIO para los LEDs"""
        # current_mode = GPIO.getmode()
        # if current_mode is None:
        #     GPIO.setmode(GPIO.BCM)
        #     logger.debug("Modo GPIO configurado en BCM.")
        # elif current_mode != GPIO.BCM:
        #     logger.warning(f"GPIO ya estaba configurado en otro modo ({current_mode}), se mantiene sin cambio.")

        GPIO.setup(self.led_verde, GPIO.OUT)
        GPIO.setup(self.led_rojo, GPIO.OUT)
        self.led_off()

    def led_off(self):
        """Apagar ambos LEDs"""
        GPIO.output(self.led_verde, GPIO.LOW)
        GPIO.output(self.led_rojo, GPIO.LOW)

    def controlar_leds(self, autorizado):
        """Controlar LEDs según autorización"""
        self.led_off()
        if autorizado:
            GPIO.output(self.led_verde, GPIO.HIGH)
            time.sleep(2)
            GPIO.output(self.led_verde, GPIO.LOW)
        else:
            GPIO.output(self.led_rojo, GPIO.HIGH)
            time.sleep(2)
            GPIO.output(self.led_rojo, GPIO.LOW)

    def leer_rfid(self):
        """Leer tarjeta RFID y devolver el ID"""
        try:
            id, text = self.reader.read()
            return str(id).zfill(8)
        except Exception as e:
            logger.error(f"Error leyendo RFID: {e}")
            return None

    def verificar_autorizacion(self, identificacion):
        """Verificar si la identificación está en la base de datos"""
        try:
            funcionario = obtener_funcionario_por_id(identificacion)
            autorizado = funcionario is not None
            logger.debug(f"Verificación de autorización para {identificacion}: {'autorizado' if autorizado else 'denegado'}")
            return autorizado
        except Exception as e:
            logger.exception(f"Error verificando autorización: {e}")
            return False

    def procesar_rfid(self, identificacion):
        """Procesar una lectura RFID completa"""
        try:
            logger.info(f"RFID leído: {identificacion}")
            autorizado = self.verificar_autorizacion(identificacion)
            self.controlar_leds(autorizado)

            success, mensaje = agregar_evento(identificacion, autorizado, 'rfid')
            if success:
                logger.info(f"Evento RFID registrado: {identificacion} - {'AUTORIZADO' if autorizado else 'DENEGADO'}")
            else:
                logger.error(f"Error registrando evento: {mensaje}")

            return autorizado

        except Exception as e:
            logger.exception(f"Error procesando RFID {identificacion}: {e}")
            return False

    def run(self):
        """Ejecutar el lector RFID en bucle continuo"""
        logger.info("📡 Lector RFID iniciado. Esperando tarjetas...")

        while self.running:
            try:
                identificacion = self.leer_rfid()
                if identificacion:
                    thread = threading.Thread(
                        target=self.procesar_rfid,
                        args=(identificacion,),
                        daemon=True,
                        name=f"RFID-{identificacion}"
                    )
                    thread.start()

            except KeyboardInterrupt:
                logger.warning("🛑 Deteniendo lector RFID...")
                self.running = False
                break
            except Exception as e:
                logger.exception(f"Error en bucle principal: {e}")
                time.sleep(1)

        self.cleanup()

    def cleanup(self):
        """Limpieza de GPIO"""
        self.led_off()
        GPIO.cleanup()
        logger.info("🧹 GPIO limpiado correctamente.")


# =============================
# 🔄 CONTROL GLOBAL DEL SERVICIO
# =============================

lector_thread = None
lector_iniciado = False


def iniciar_lector_rfid():
    """Inicia el lector RFID solo una vez"""
    global lector_iniciado, lector_thread
    if lector_iniciado:
        logger.warning("Lector RFID ya en ejecución, no se reinicia.")
        return lector_thread

    try:
        lector = RFIDReader()
        lector_thread = threading.Thread(target=lector.run, daemon=True, name="RFID-Main")
        lector_thread.start()
        lector_iniciado = True
        logger.info("✅ Servicio RFID iniciado correctamente.")
        return lector_thread
    except Exception as e:
        logger.exception(f"❌ Error iniciando lector RFID: {e}")
        return None
