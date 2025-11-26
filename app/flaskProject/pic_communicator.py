import serial
import threading
import time
from database import agregar_evento, agregar_funcionario, eliminar_funcionario, obtener_funcionario_por_id

# Configuración del puerto serial para Raspberry Pi 2
SERIAL_PORT = '/dev/ttyAMA0'
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
                timeout=1
            )
            print("Conexión serial establecida con PIC")
        except Exception as e:
            print(f"Error al conectar con PIC: {e}")

    def enviar_comando_pic(self, comando, cedula):
        """Envía comandos A (Alta) o B (Baja) al PIC"""
        try:
            if self.ser and self.ser.is_open:
                mensaje = f"{comando}{cedula}"
                self.ser.write(mensaje.encode('utf-8'))
                print(f"Comando enviado al PIC: {mensaje}")
                return True
            else:
                print("Puerto serial no disponible")
                return False
        except Exception as e:
            print(f"Error enviando comando al PIC: {e}")
            return False

    def leer_eventos_pic(self):
        """Lee eventos del PIC en segundo plano"""
        try:
            if self.ser and self.ser.is_open:
                while True:
                    if self.ser.in_waiting > 0:
                        linea = self.ser.readline().decode('utf-8').strip()
                        self.procesar_evento_pic(linea)
                    time.sleep(0.1)
        except Exception as e:
            print(f"Error leyendo del PIC: {e}")

    def procesar_evento_pic(self, linea):
        """Procesa eventos recibidos del PIC"""
        try:
            print(f"Evento recibido del PIC: {linea}")

            # Procesar eventos de códigos de barras
            if linea.startswith("tiempo="):
                # Formato: "tiempo=0000, cedula=12345678, autorizado=Si/No, operacion=acceso/alta/baja"
                partes = linea.split(', ')
                if len(partes) == 4:
                    cedula = partes[1].split('=')[1]
                    autorizado_str = partes[2].split('=')[1]
                    autorizado = 1 if autorizado_str == 'Si' else 0
                    operacion_str = partes[3].split('=')[1]

                    # Registrar evento en base de datos
                    agregar_evento(cedula, autorizado, operacion_str, 'serial')
                    print(f"Evento registrado: {cedula} - {'Autorizado' if autorizado else 'Denegado'}")

                    success = False
                    if operacion_str == "Alta" and autorizado == 1:
                        success, _ = agregar_funcionario(cedula, "")
                    elif operacion_str == "Baja" and autorizado == 1:
                        success, _ = eliminar_funcionario(cedula)

                    if success:
                        print(f"Confirmación PIC: {linea}")

        except Exception as e:
            print(f"Error procesando evento PIC: {e}")

# Instancia global del comunicador
pic_comm = PICCommunicator()

def dar_de_alta_funcionario_en_pic(identificacion):
    pic_comm.enviar_comando_pic('A', identificacion)

# Funciones de sincronización con PIC
def agregar_funcionario_con_sinc(identificacion, nombre, es_cedula):
    """Agrega funcionario y sincroniza con PIC"""
    success, mensaje = agregar_funcionario(identificacion, nombre)

    if success and es_cedula:
        # Enviar comando de ALTA al PIC
        # Consideramos que si tiene 8 digitos es una cedula
        if pic_comm.enviar_comando_pic('A', identificacion):
            mensaje += " - Sincronizado con PIC"
        else:
            mensaje += " - Error sincronizando con PIC"

    return success, mensaje


def eliminar_funcionario_con_sinc(identificacion, es_cedula):
    """Elimina funcionario y sincroniza con PIC"""
    success, mensaje = eliminar_funcionario(identificacion)

    if success and es_cedula:
        # Enviar comando de BAJA al PIC
        if pic_comm.enviar_comando_pic('B', identificacion):
            mensaje += " - Sincronizado con PIC"
        else:
            mensaje += " - Error sincronizando con PIC"

    return success, mensaje


# Iniciar hilo para leer eventos del PIC
def iniciar_lector_pic():
    thread = threading.Thread(target=pic_comm.leer_eventos_pic, daemon=True)
    thread.start()
    print("Lector de eventos PIC iniciado")