from gpiozero import LED
import time
import logging
import traceback
from logger_config import setup_logger

logger = setup_logger("alarma", "alarma.log", level=logging.INFO)

GPIO_ALARMA = 25

# Inicializamos el LED usando gpiozero
try:
    alarma_led = LED(GPIO_ALARMA)
    logger.info("LED de alarma inicializado correctamente con gpiozero")
except Exception as e:
    logger.error(f"Error inicializando LED de alarma: {e}")
    logger.error(traceback.format_exc())


def activar_alarma_led(duracion=5):
    """
    Enciende el LED de alarma durante 'duracion' segundos.
    """
    logger.warning(f"ALARMA ACTIVADA — LED encendido por {duracion} segundos")

    try:
        alarma_led.on()
        time.sleep(duracion)
    except Exception as e:
        logger.error(f"Error durante activación de alarma LED: {e}")
        logger.error(traceback.format_exc())
    finally:
        alarma_led.off()
        logger.info("LED de alarma apagado")


def apagar_alarma_led():
    """
    Apaga manualmente el LED de alarma.
    """
    try:
        alarma_led.off()
        logger.info("LED de alarma apagado manualmente")
    except Exception as e:
        logger.error(f"Error apagando alarma LED: {e}")
        logger.error(traceback.format_exc())
