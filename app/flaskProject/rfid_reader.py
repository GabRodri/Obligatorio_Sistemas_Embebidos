import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
from time import sleep
import threading
import time
import traceback
from datetime import datetime, timedelta

from database import obtener_funcionario_por_id, agregar_evento, obtener_intentos_fallidos_recientes
from logger_config import setup_logger
import logging

# ===============================
# 🔧 LOGGER PROFESIONAL (ROTATING)
# ===============================
logger = setup_logger("rfid", "rfid_reader.log", level=logging.INFO)

GPIO.setwarnings(False)
DEBUG = True

def activar_alarma(identificacion, intentos):
    logger.warning(f"ALARMA DISPARADA para {identificacion}. Intentos={intentos}")
    agregar_evento(identificacion, autorizado="No", operacion="Acceso", canal="Alarma")

    # todo: Mostrar mensaje en globo en pagina WEB "ALARMA - INTENTO REITERADO DE ACCESO"

class RFIDReader:
    def __init__(self):
        try:
            self.reader = SimpleMFRC522()
            self.running = True
            self.ultimo_rfid_leido = None
            self.ultimo_rfid_leido_dt = None
            logger.info("RFIDReader inicializado correctamente")

        except Exception as e:
            logger.error(f"Error inicializando RFIDReader: {e}")
            logger.error(traceback.format_exc())
            raise
    # def setup_gpio(self):
    #     try:
    #         GPIO.setup(self.led_verde, GPIO.OUT)
    #         GPIO.setup(self.led_rojo, GPIO.OUT)
    #         self.led_off()
    #         logger.info("GPIO del lector RFID configurado correctamente")
    #     except Exception as e:
    #         logger.error(f"Error configurando GPIO en RFIDReader: {e}")
    #         logger.error(traceback.format_exc())
    #         raise
    #
    # def led_off(self):
    #     try:
    #         GPIO.output(self.led_verde, GPIO.LOW)
    #         GPIO.output(self.led_rojo, GPIO.LOW)
    #     except Exception as e:
    #         logger.error(f"Error apagando LEDs: {e}")
    #         logger.error(traceback.format_exc())
    #
    # def controlar_leds(self, autorizado):
    #     try:
    #         self.led_off()
    #         led = self.led_verde if autorizado else self.led_rojo
    #
    #         GPIO.output(led, GPIO.HIGH)
    #         time.sleep(5)
    #         GPIO.output(led, GPIO.LOW)
    #
    #     except Exception as e:
    #         logger.error(f"Error controlando LEDs: {e}")
    #         logger.error(traceback.format_exc())
    def leer_rfid(self):
        try:

            logger.info("Entro en leer rfid")
            id, _ = self.reader.read()
            logger.info("ya leyo")
            logger.info(id)

            return str(id).zfill(8)
        except Exception as e:
            logger.error(f"Error leyendo RFID: {e}")
            logger.error(traceback.format_exc())
            return None

    def verificar_autorizacion(self, identificacion):
        try:
            funcionario = obtener_funcionario_por_id(identificacion)
            autorizado = funcionario is not None
            logger.info(f"Verificación RFID {identificacion}: {'AUTORIZADO' if autorizado else 'DENEGADO'}")
            return autorizado
        except Exception as e:
            logger.error(f"Error verificando autorización RFID: {e}")
            logger.error(traceback.format_exc())
            return False

    def  procesar_rfid(self, identificacion):
        try:
            logger.info(f"RFID leído: {identificacion}")
            autorizado = self.verificar_autorizacion(identificacion)
            success, mensaje = agregar_evento(identificacion, autorizado, "rfid", "rfid")

            if success and autorizado == 0:

                fecha = (datetime.now() - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
                self.logger.info(f"CONSULTANDO FECHA {fecha}")
                intentos = obtener_intentos_fallidos_recientes(identificacion, minutos=1)
                logger.info(f"Intentos fallidos de {identificacion}: {intentos}")

                if intentos >= 3:
                    activar_alarma(identificacion, intentos)

            if success:
                logger.info(f"Evento RFID registrado: {identificacion} - {'AUTORIZADO' if autorizado else 'DENEGADO'}")
            else:
                logger.error(f"Error registrando evento RFID: {mensaje}")
                logger.error(traceback.format_exc())
            return autorizado

        except Exception as e:
            logger.error(f"Error procesando RFID {identificacion}: {e}")
            logger.error(traceback.format_exc())
            return False

    def run(self):
        logger.info("📡 Lector RFID iniciado. Esperando tarjetas...")

        while self.running:
            try:
                identificacion = self.leer_rfid()

                logger.info("TEST")
                logger.info(identificacion)

                now = datetime.now()

                if (identificacion and (identificacion != self.ultimo_rfid_leido or (now - self.ultimo_rfid_leido_dt).total_seconds() > 5)):
                    self.ultimo_rfid_leido = identificacion
                    self.ultimo_rfid_leido_dt = now

                    thread = threading.Thread(
                        target=self.procesar_rfid,
                        args=(identificacion,),
                        daemon=True,
                        name=f"RFID-{identificacion}"
                    )
                    thread.start()

                else:
                    if DEBUG and identificacion:
                        logger.info("Lectura RFID ignorada por repetición o timeout")
                        sleep(4)

            except KeyboardInterrupt:
                logger.warning("🛑 Deteniendo lector RFID por teclado…")
                self.running = False
                break

            except Exception as e:
                logger.error(f"Error en bucle principal del lector RFID: {e}")
                logger.error(traceback.format_exc())
                time.sleep(1)

        self.cleanup()

    def cleanup(self):
        try:
            GPIO.cleanup()
            logger.info("GPIO del lector RFID limpiado correctamente")
        except Exception as e:
            logger.error(f"Error en cleanup() del lector RFID: {e}")
            logger.error(traceback.format_exc())


# =============================
# 🔄 CONTROL GLOBAL DEL SERVICIO
# =============================

lector_thread = None
lector_iniciado = False


def iniciar_lector_rfid():
    global lector_iniciado, lector_thread

    if lector_iniciado:
        logger.warning("Lector RFID ya está en ejecución. No se reinicia.")
        return lector_thread

    try:
        lector = RFIDReader()
        lector_thread = threading.Thread(
            target=lector.run, daemon=True, name="RFID-Main"
        )
        lector_thread.start()

        lector_iniciado = True
        logger.info("Servicio RFID iniciado correctamente.")
        return lector_thread

    except Exception as e:
        logger.error(f"Error iniciando servicio RFID: {e}")
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":

    lector = RFIDReader()
    lector.run()