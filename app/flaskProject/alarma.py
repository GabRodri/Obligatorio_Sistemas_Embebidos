import RPi.GPIO as GPIO
import time
import logging
import traceback
from logger_config import setup_logger

logger = setup_logger("alarma", "alarma.log", level=logging.INFO)

GPIO_ALARMA = 27

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

try:
    GPIO.setup(GPIO_ALARMA, GPIO.OUT, initial=GPIO.LOW)
    logger.info("GPIO de alarma inicializado correctamente")
except Exception as e:
    logger.error(f"Error inicializando GPIO de alarma: {e}")
    logger.error(traceback.format_exc())


def activar_alarma_led(duracion=5):
    try:
        logger.warning(f"ALARMA ACTIVADA — LED encendido por {duracion} segundos")
        GPIO.output(GPIO_ALARMA, GPIO.HIGH)
        time.sleep(duracion)
    except Exception as e:
        logger.error(f"Error durante activación de alarma LED: {e}")
        logger.error(traceback.format_exc())
    finally:
        GPIO.output(GPIO_ALARMA, GPIO.LOW)
        logger.info("LED de alarma apagado")


def apagar_alarma_led():
    try:
        GPIO.output(GPIO_ALARMA, GPIO.LOW)
        logger.info("LED de alarma apagado manualmente")
    except Exception as e:
        logger.error(f"Error apagando alarma LED: {e}")
        logger.error(traceback.format_exc())
