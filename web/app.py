from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from database import *
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_mensajes_flash'

@app.route('/')
def index():
    estadisticas = obtener_estadisticas()
    return render_template('index.html', estadisticas=estadisticas)

# Rutas para Funcionarios
@app.route('/funcionarios')
def gestion_funcionarios():
    funcionarios = obtener_funcionarios()
    return render_template('funcionarios.html', funcionarios=funcionarios)

@app.route('/agregar_funcionario', methods=['POST'])
def agregar_funcionario_route():
    identificacion = request.form['identificacion']
    nombre = request.form['nombre']
    
    success, mensaje = agregar_funcionario(identificacion, nombre)
    
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
    success, mensaje = eliminar_funcionario(identificacion)
    
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

if __name__ == '__main__':
    print("Iniciando Sistema de Gestión de Eventos y Funcionarios...")
    print("Base de datos: Database.db")
    print("Accede a la aplicación en: http://localhost:5000")
    print("API disponible en: http://localhost:5000/api/evento")
    app.run(debug=True, host='0.0.0.0', port=5000)