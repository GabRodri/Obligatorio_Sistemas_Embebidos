from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from database import *
from rfid_reader import iniciar_lector_rfid
from pic_communicator import iniciar_lector_pic, agregar_funcionario_con_sinc, eliminar_funcionario_con_sinc

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_mensajes_flash'

# Estado del sistema
sistema_activo = True


@app.route('/')
def index():
    estadisticas = obtener_estadisticas()
    return render_template('index.html',
                           estadisticas=estadisticas,
                           sistema_activo=sistema_activo)


@app.route('/control_sistema', methods=['POST'])
def control_sistema():
    global sistema_activo
    accion = request.form.get('accion')

    if accion == 'activar':
        sistema_activo = True
        flash('Sistema activado', 'success')
    elif accion == 'desactivar':
        sistema_activo = False
        flash('Sistema desactivado', 'warning')

    return redirect(url_for('index'))


# Rutas para Funcionarios
@app.route('/funcionarios')
def gestion_funcionarios():
    funcionarios = obtener_funcionarios()
    return render_template('funcionarios.html', funcionarios=funcionarios)


@app.route('/agregar_funcionario', methods=['POST'])
def agregar_funcionario_route():
    identificacion = request.form['identificacion']
    nombre = request.form['nombre']

    success, mensaje = agregar_funcionario_con_sinc(identificacion, nombre)

    if success:
        flash(mensaje, 'success')
    else:
        flash(mensaje, 'error')

    return redirect(url_for('gestion_funcionarios'))


@app.route('/modificar_funcionario', methods=['POST'])
def modificar_funcionario_route():
    identificacion = request.form['identificacion']
    nuevo_nombre = request.form['nuevo_nombre']

    success, mensaje = modificar_funcionario(identificacion, nuevo_nombre)

    if success:
        flash(mensaje, 'success')
    else:
        flash(mensaje, 'error')

    return redirect(url_for('gestion_funcionarios'))


@app.route('/eliminar_funcionario/<identificacion>')
def eliminar_funcionario_route(identificacion):
    success, mensaje = eliminar_funcionario_con_sinc(identificacion)

    if success:
        flash(mensaje, 'success')
    else:
        flash(mensaje, 'error')

    return redirect(url_for('gestion_funcionarios'))


# Rutas para Eventos
@app.route('/eventos')
def ver_eventos():
    eventos = obtener_eventos()
    return render_template('eventos.html', eventos=eventos)


@app.route('/consultar_eventos', methods=['GET', 'POST'])
def consultar_eventos():
    eventos = []
    fecha_inicio = ""
    fecha_fin = ""

    if request.method == 'POST':
        fecha_inicio = request.form['fecha_inicio']
        fecha_fin = request.form['fecha_fin']

        # Validar que las fechas no estén vacías
        if fecha_inicio and fecha_fin:
            eventos = consultar_eventos_por_fecha(fecha_inicio, fecha_fin)
            if eventos:
                flash(f'Se encontraron {len(eventos)} eventos en el rango seleccionado', 'info')
            else:
                flash('No se encontraron eventos en el rango seleccionado', 'warning')
        else:
            flash('Por favor, seleccione ambas fechas', 'error')

    return render_template('consultar_eventos.html',
                           eventos=eventos,
                           fecha_inicio=fecha_inicio,
                           fecha_fin=fecha_fin)


# API para recibir eventos desde sistemas externos
@app.route('/api/evento', methods=['POST'])
def api_evento():
    try:
        data = request.get_json()
        identificacion = data.get('identificacion')
        canal = data.get('canal', 'rfid')

        if not identificacion:
            return jsonify({'status': 'error', 'message': 'Identificación requerida'}), 400

        # Verificar si el funcionario existe
        funcionario = obtener_funcionario_por_id(identificacion)
        autorizado = 1 if funcionario else 0

        success, mensaje = agregar_evento(identificacion, autorizado, canal)

        if success:
            return jsonify({
                'status': 'success',
                'autorizado': bool(autorizado),
                'funcionario_existe': bool(funcionario),
                'nombre_funcionario': funcionario[1] if funcionario else None,
                'message': mensaje
            })
        else:
            return jsonify({'status': 'error', 'message': mensaje}), 400

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


# Ruta para obtener estadísticas en JSON
@app.route('/api/estadisticas')
def api_estadisticas():
    estadisticas = obtener_estadisticas()
    return jsonify(estadisticas)


# Ruta para estado del sistema RFID
@app.route('/api/rfid_status')
def rfid_status():
    return jsonify({
        'sistema_activo': sistema_activo,
        'rfid_activo': True
    })


# # Iniciar todos los servicios al arrancar
# @app.before_first_request
# def iniciar_servicios():
#     print("Iniciando todos los servicios...")
#
#     # Iniciar lector RFID
#     iniciar_lector_rfid()
#
#     # Iniciar comunicación con PIC
#     try:
#         iniciar_lector_pic()
#         print("Comunicación con PIC iniciada")
#     except Exception as e:
#         print(f"Error iniciando comunicación PIC: {e}")
#
#     print("Todos los servicios iniciados")


if __name__ == '__main__':

    print("Iniciando todos los servicios...")

    # Iniciar lector RFID
    iniciar_lector_rfid()

    # Iniciar comunicación con PIC
    try:
        iniciar_lector_pic()
        print("Comunicación con PIC iniciada")
    except Exception as e:
        print(f"Error iniciando comunicación PIC: {e}")

    print("Todos los servicios iniciados")

    print("=" * 60)
    print("SISTEMA DE GESTIÓN DE ACCESOS - RASPBERRY PI 2")
    print("=" * 60)
    print("Servicios Iniciados:")
    print("  ✅ Servidor Web: http://localhost:5000")
    print("  ✅ Lector RFID: Activo (GPIO 17-27 para LEDs)")
    print("  ✅ Comunicación Serial: /dev/ttyAMA0")
    print("  ✅ Base de datos: Database.db")
    print("  ✅ API REST: /api/evento, /api/estadisticas")
    print("=" * 60)

    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)