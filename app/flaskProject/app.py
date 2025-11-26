import traceback
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from database import *
from pic_communicator import (
    iniciar_lector_pic,
    agregar_funcionario_con_sinc,
    eliminar_funcionario_con_sinc,
    dar_de_alta_funcionario_en_pic,
)
from time import sleep
from alarma import activar_alarma_led
from rfid_reader import iniciar_lector_rfid
from logger_config import setup_logger

logger = setup_logger("app", "app.log", level=logging.INFO)

app = Flask(__name__)
app.secret_key = "clave_secreta_para_mensajes_flash"

sistema_activo = True


def activar_alarma(identificacion, intentos):
    logger.warning(f"ALARMA DISPARADA para {identificacion}. Intentos={intentos}")
    activar_alarma_led(duracion=5)


@app.route("/")
def index():
    try:
        logger.info("Acceso a / desde UI")
        estadisticas = obtener_estadisticas()
        return render_template(
            "index.html", estadisticas=estadisticas, sistema_activo=sistema_activo
        )
    except Exception as e:
        logger.error(f"Error en ruta / : {e}")
        logger.error(traceback.format_exc())
        raise


@app.route("/control_sistema", methods=["POST"])
def control_sistema():
    global sistema_activo
    try:
        accion = request.form.get("accion")
        logger.info(f"Control del sistema: acción={accion}")

        if accion == "activar":
            sistema_activo = True
        elif accion == "desactivar":
            sistema_activo = False

        return redirect(url_for("index"))

    except Exception as e:
        logger.error(f"Error en control_sistema: {e}")
        logger.error(traceback.format_exc())
        raise


@app.route("/funcionarios")
def gestion_funcionarios():
    try:
        logger.info("Acceso a /funcionarios")
        funcionarios = obtener_funcionarios()
        return render_template("funcionarios.html", funcionarios=funcionarios)
    except Exception as e:
        logger.error(f"Error en /funcionarios: {e}")
        logger.error(traceback.format_exc())
        raise


def verificar_si_es_cedula(identificacion):
    if len(identificacion) == 8 and identificacion.isdigit():
        return True, "serial"
    elif len(identificacion) < 8:
        return False, ""
    else:
        return False, "rfid"


@app.route("/sincronizar_funcionarios_pic", methods=["POST"])
def sincronizar_funcionarios_pic():
    try:
        logger.info("Inicio sincronización masiva con PIC")

        funcionarios = obtener_funcionarios()
        total_enviados = 0
        total_ignorados = 0

        for identificacion, nombre in funcionarios:
            es_cedula, canal = verificar_si_es_cedula(identificacion)

            if es_cedula:
                logger.info(f"Enviando {identificacion} al PIC")
                dar_de_alta_funcionario_en_pic(identificacion)
                total_enviados += 1
                sleep(1)
            else:
                total_ignorados += 1

        logger.info(
            f"Sincronización completada. Enviados={total_enviados}, Ignorados={total_ignorados}"
        )

        flash(
            f"Se enviaron {total_enviados} funcionarios al PIC. "
            f"{total_ignorados} fueron ignorados por no ser cédula.",
            "success",
        )

        return redirect(url_for("gestion_funcionarios"))

    except Exception as e:
        logger.error(f"Error sincronizando funcionarios con PIC: {e}")
        logger.error(traceback.format_exc())
        raise


@app.route("/agregar_funcionario", methods=["POST"])
def agregar_funcionario_route():
    identificacion = request.form["identificacion"]
    nombre = request.form["nombre"]

    try:
        logger.info(f"Alta funcionario: {identificacion} - {nombre}")

        es_cedula, canal = verificar_si_es_cedula(identificacion)
        success, mensaje = agregar_funcionario_con_sinc(
            identificacion, nombre, es_cedula
        )

        if success:
            agregar_evento(identificacion, "Si", "Alta", canal)
            logger.info(f"Funcionario agregado OK: {identificacion}")
            flash(mensaje, "success")
        else:
            agregar_evento(identificacion, "No", "Alta", canal)
            logger.error(f"Error alta funcionario {identificacion}: {mensaje}")
            flash(mensaje, "error")

        return redirect(url_for("gestion_funcionarios"))

    except Exception as e:
        logger.error(f"Excepción en agregar_funcionario: {e}")
        logger.error(traceback.format_exc())
        raise


@app.route("/modificar_funcionario", methods=["POST"])
def modificar_funcionario_route():
    identificacion = request.form["identificacion"]
    nuevo_nombre = request.form["nuevo_nombre"]

    try:
        logger.info(f"Modificación funcionario {identificacion} → {nuevo_nombre}")

        _, canal = verificar_si_es_cedula(identificacion)
        success, mensaje = modificar_funcionario(identificacion, nuevo_nombre)

        if success:
            agregar_evento(identificacion, "Si", "Modificación", canal)
            logger.info(f"Modificación OK para {identificacion}")
            flash(mensaje, "success")
        else:
            agregar_evento(identificacion, "No", "Modificación", canal)
            logger.error(f"Error modificando {identificacion}: {mensaje}")
            flash(mensaje, "error")

        return redirect(url_for("gestion_funcionarios"))

    except Exception as e:
        logger.error(f"Excepción en modificar_funcionario: {e}")
        logger.error(traceback.format_exc())
        raise


@app.route("/eliminar_funcionario/<identificacion>")
def eliminar_funcionario_route(identificacion):
    try:
        logger.info(f"Baja solicitada para {identificacion}")

        es_cedula, canal = verificar_si_es_cedula(identificacion)
        success, mensaje = eliminar_funcionario_con_sinc(identificacion, es_cedula)

        if success:
            agregar_evento(identificacion, "Si", "Baja", canal)
            logger.info(f"Baja OK de {identificacion}")
            flash(mensaje, "success")
        else:
            agregar_evento(identificacion, "No", "Baja", canal)
            logger.error(f"Error baja {identificacion}: {mensaje}")
            flash(mensaje, "error")

        return redirect(url_for("gestion_funcionarios"))

    except Exception as e:
        logger.error(f"Excepción en eliminar_funcionario: {e}")
        logger.error(traceback.format_exc())
        raise


@app.route("/eventos")
def ver_eventos():
    try:
        logger.info("Acceso a /eventos")
        eventos = obtener_eventos()
        return render_template("eventos.html", eventos=eventos)
    except Exception as e:
        logger.error(f"Error en /eventos: {e}")
        logger.error(traceback.format_exc())
        raise


@app.route("/consultar_eventos", methods=["GET", "POST"])
def consultar_eventos():
    try:
        logger.info("Acceso a /consultar_eventos")

        eventos = []
        fecha_inicio = ""
        fecha_fin = ""

        if request.method == "POST":
            fecha_inicio = request.form["fecha_inicio"]
            fecha_fin = request.form["fecha_fin"]

            logger.info(f"Consulta eventos {fecha_inicio} → {fecha_fin}")

            if fecha_inicio and fecha_fin:
                eventos = consultar_eventos_por_fecha(fecha_inicio, fecha_fin)
                logger.info(f"Resultados: {len(eventos)} eventos")
            else:
                logger.warning("Consulta inválida (fechas incompletas)")

        return render_template(
            "consultar_eventos.html",
            eventos=eventos,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )

    except Exception as e:
        logger.error(f"Excepción en consultar_eventos: {e}")
        logger.error(traceback.format_exc())
        raise


@app.route("/api/evento", methods=["POST"])
def api_evento():
    try:
        data = request.get_json()
        logger.info(f"API evento recibido: {data}")

        identificacion = data.get("identificacion")
        canal = data.get("canal", "rfid")

        if not identificacion:
            logger.warning("Evento API sin identificación")
            return jsonify({"status": "error", "message": "Identificación requerida"}), 400

        funcionario = obtener_funcionario_por_id(identificacion)
        autorizado = 1 if funcionario else 0

        success, mensaje = agregar_evento(identificacion, autorizado, "api", canal)

        if success and autorizado == 0:
            intentos = obtener_intentos_fallidos_recientes(identificacion, minutos=1)
            logger.info(f"Intentos fallidos de {identificacion}: {intentos}")

            if intentos >= 3:
                activar_alarma(identificacion, intentos)

        if success:
            logger.info(f"Evento API OK: {identificacion}, autorizado={autorizado}")
            return jsonify({
                "status": "success",
                "autorizado": bool(autorizado),
                "funcionario_existe": bool(funcionario),
                "nombre_funcionario": funcionario[1] if funcionario else None,
                "message": mensaje,
            })
        else:
            logger.error(f"Error registrando evento API: {mensaje}")
            return jsonify({"status": "error", "message": mensaje}), 400

    except Exception as e:
        logger.error(f"Excepción en /api/evento: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/estadisticas")
def api_estadisticas():
    return jsonify(obtener_estadisticas())


@app.route("/api/rfid_status")
def rfid_status():
    return jsonify({"sistema_activo": sistema_activo, "rfid_activo": True})


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("SISTEMA DE GESTIÓN DE ACCESOS - RASPBERRY PI")
    logger.info("=" * 60)

    try:
        logger.info("Iniciando lector PIC…")
        iniciar_lector_pic()


        logger.info("Iniciando lector RFID…")
        iniciar_lector_rfid()

    except Exception as e:
        logger.error(f"Error iniciando lector PIC: {e}")
        logger.error(traceback.format_exc())

    logger.info("Servicios inicializados.")
    logger.info("Servidor en http://localhost:5000")
    logger.info("Base de datos: Database.db")
    logger.info("=" * 60)

    app.run(debug=False, host="0.0.0.0", port=5000, threaded=True)