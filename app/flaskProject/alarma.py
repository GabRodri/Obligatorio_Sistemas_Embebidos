# import time
# import logging
# import traceback
# from logger_config import setup_logger
#
# logger = setup_logger("alarma", "alarma.log", level=logging.INFO)
#
#
# def activar_alarma_led():
#     try:
#         logger.warning(f"ALARMA ACTIVADA — LED encendido por {duracion} segundos")
#
#         time.sleep(duracion)
#     except Exception as e:
#         logger.error(f"Error durante activación de alarma LED: {e}")
#         logger.error(traceback.format_exc())
#     finally:
#         GPIO.output(GPIO_ALARMA, GPIO.LOW)
#         logger.info("LED de alarma apagado")
# #
# #
# # def apagar_alarma_led():
# #     try:
# #         GPIO.output(GPIO_ALARMA, GPIO.LOW)
# #         logger.info("LED de alarma apagado manualmente")
# #     except Exception as e:
# #         logger.error(f"Error apagando alarma LED: {e}")
# #         logger.error(traceback.format_exc())
