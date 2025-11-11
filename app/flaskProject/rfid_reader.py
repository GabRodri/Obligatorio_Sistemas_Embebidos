import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import threading
import time
from database import obtener_funcionario_por_id, agregar_evento


class RFIDReader:
    def __init__(self):
        self.reader = SimpleMFRC522()
        self.led_verde = 17
        self.led_rojo = 27
        self.setup_gpio()
        self.running = True

    def setup_gpio(self):
        """Configura los pines GPIO para los LEDs"""
        GPIO.setmode(GPIO.BCM)
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
            # Encender LED verde por 2 segundos
            GPIO.output(self.led_verde, GPIO.HIGH)
            time.sleep(2)
            GPIO.output(self.led_verde, GPIO.LOW)
        else:
            # Encender LED rojo por 2 segundos
            GPIO.output(self.led_rojo, GPIO.HIGH)
            time.sleep(2)
            GPIO.output(self.led_rojo, GPIO.LOW)

    def leer_rfid(self):
        """Leer tarjeta RFID y devolver el ID"""
        try:
            id, text = self.reader.read()
            return str(id).zfill(8)  # Convertir a string de 8 dígitos
        except Exception as e:
            print(f"Error leyendo RFID: {e}")
            return None

    def verificar_autorizacion(self, identificacion):
        """Verificar si la identificación está en la base de datos"""
        try:
            funcionario = obtener_funcionario_por_id(identificacion)
            return funcionario is not None
        except Exception as e:
            print(f"Error verificando autorización: {e}")
            return False

    def procesar_rfid(self, identificacion):
        """Procesar una lectura RFID completa"""
        try:
            print(f"RFID leído: {identificacion}")

            # Verificar autorización
            autorizado = self.verificar_autorizacion(identificacion)

            # Controlar LEDs
            self.controlar_leds(autorizado)

            # Registrar evento en base de datos
            success, mensaje = agregar_evento(identificacion, autorizado, 'rfid')

            if success:
                print(f"Evento RFID registrado: {identificacion} - {'AUTORIZADO' if autorizado else 'DENEGADO'}")
            else:
                print(f"Error registrando evento: {mensaje}")

            return autorizado

        except Exception as e:
            print(f"Error procesando RFID: {e}")
            return False

    def run(self):
        """Ejecutar el lector RFID en bucle continuo"""
        print("Lector RFID iniciado. Esperando tarjetas...")

        while self.running:
            try:
                # Leer RFID
                identificacion = self.leer_rfid()

                if identificacion:
                    # Procesar en un hilo separado para no bloquear nuevas lecturas
                    thread = threading.Thread(
                        target=self.procesar_rfid,
                        args=(identificacion,)
                    )
                    thread.daemon = True
                    thread.start()

            except KeyboardInterrupt:
                print("Deteniendo lector RFID...")
                self.running = False
                break
            except Exception as e:
                print(f"Error en bucle RFID: {e}")
                time.sleep(1)

        self.cleanup()

    def cleanup(self):
        """Limpieza de GPIO"""
        self.led_off()
        GPIO.cleanup()
        print("GPIO limpiado")

lector_activo = False

def iniciar_lector_rfid():
    """Iniciar el lector RFID en un hilo separado (solo una vez)"""
    global lector_activo
    if lector_activo:
        print("⚠️ Lector RFID ya está en ejecución, se omite reinicio.")
        return

    lector = RFIDReader()
    thread = threading.Thread(target=lector.run, daemon=True)
    thread.start()
    lector_activo = True
    print("✅ Servicio RFID iniciado")
