import serial
import threading
import time
import logging
import traceback

from database import (
    agregar_evento,
    agregar_funcionario,
    eliminar_funcionario,
    obtener_funcionario_por_id,
)

from logger_config import setup_logger

# Logger específico para este módulo
logger = setup_logger("pic", "pic.log", level=logging.INFO)

SERIAL_PORT = "/dev/ttyAMA0"
BAUD_RATE = 9600


class PICCommunicator:
    def __init__(self):
        self.ser = None
        self.init_serial()

    def init_serial(self):
        try:
            self.ser = serial.Serial(
                port=SERIAL_PORT,
                baudrate=BAUD_RATE,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=1,
            )
            logger.info("Conexión serial establecida con PIC")
        except Exception as e:
            logger.error(f"Error al conectar con PIC: {e}")
            logger.error(traceback.format_exc())

    def enviar_comando_pic(self, comando, cedula):
        try:
            if self.ser and self.ser.is_open:
                mensaje = f"{comando}{cedula}"
                self.ser.write(mensaje.encode("utf-8"))
                logger.info(f"Comando enviado al PIC: {mensaje}")
                return True
            else:
                logger.warning("Puerto serial no disponible para enviar comando")
                return False
        except Exception as e:
            logger.error(f"Error enviando comando al PIC: {e}")
            logger.error(traceback.format_exc())
            return False

    def leer_eventos_pic(self):
        try:
            if self.ser and self.ser.is_open:
                logger.info("Lector de eventos PIC activo")
                while True:
                    try:
                        if self.ser.in_waiting > 0:
                            linea = self.ser.readline().decode("utf-8").strip()
                            if linea:
                                self.procesar_evento_pic(linea)
                    except Exception as inner:
                        logger.error(f"Error en lectura individual del PIC: {inner}")
                        logger.error(traceback.format_exc())
                    time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error leyendo del PIC: {e}")
            logger.error(traceback.format_exc())

    def procesar_evento_pic(self, linea):
        try:
            logger.info(f"Evento recibido del PIC: {linea}")

            if linea.startswith("tiempo="):
                partes = linea.split(", ")
                if len(partes) == 4:
                    cedula = partes[1].split("=")[1]
                    autorizado_str = partes[2].split("=")[1]
                    autorizado = 1 if autorizado_str == "Si" else 0
                    operacion_str = partes[3].split("=")[1]

                    agregar_evento(cedula, autorizado, operacion_str, "serial")

                    logger.info(
                        f"Evento registrado: cedula={cedula}, autorizado={autorizado}, operacion={operacion_str}"
                    )

                    success = False
                    if operacion_str == "Alta" and autorizado == 1:
                        success, _ = agregar_funcionario(cedula, "")
                    elif operacion_str == "Baja" and autorizado == 1:
                        success, _ = eliminar_funcionario(cedula)

                    if success:
                        logger.info(f"Operación PIC procesada correctamente: {linea}")

        except Exception as e:
            logger.error(f"Error procesando evento PIC: {e}")
            logger.error(traceback.format_exc())


pic_comm = PICCommunicator()


def dar_de_alta_funcionario_en_pic(identificacion):
    ok = pic_comm.enviar_comando_pic("A", identificacion)
    if ok:
        logger.info(f"Alta enviada al PIC para {identificacion}")
    else:
        logger.warning(f"No se pudo enviar ALTA al PIC para {identificacion}")


def agregar_funcionario_con_sinc(identificacion, nombre, es_cedula):
    success, mensaje = agregar_funcionario(identificacion, nombre)

    if success and es_cedula:
        ok = pic_comm.enviar_comando_pic("A", identificacion)
        if ok:
            mensaje += " - Sincronizado con PIC"
            logger.info(f"Alta sincronizada con PIC para {identificacion}")
        else:
            mensaje += " - Error sincronizando con PIC"
            logger.warning(f"Error enviando ALTA del PIC para {identificacion}")

    return success, mensaje


def eliminar_funcionario_con_sinc(identificacion, es_cedula):
    success, mensaje = eliminar_funcionario(identificacion)

    if success and es_cedula:
        ok = pic_comm.enviar_comando_pic("B", identificacion)
        if ok:
            mensaje += " - Sincronizado con PIC"
            logger.info(f"Baja sincronizada con PIC para {identificacion}")
        else:
            mensaje += " - Error sincronizando con PIC"
            logger.warning(f"Error enviando BAJA al PIC para {identificacion}")

    return success, mensaje


def iniciar_lector_pic():
    try:
        thread = threading.Thread(target=pic_comm.leer_eventos_pic, daemon=True)
        thread.start()
        logger.info("Hilo lector del PIC iniciado")
    except Exception as e:
        logger.error(f"Error iniciando hilo lector PIC: {e}")
        logger.error(traceback.format_exc())
