from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
import mysql.connector
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import requests

app = Flask(__name__)
app.secret_key = 'clave_secreta_123'

# Conexión a MySQL
def get_db():
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST'),    # Usando la variable de entorno DB_HOST
        user=os.environ.get('DB_USER'),    # Usando la variable de entorno DB_USER
        password=os.environ.get('DB_PASSWORD'),  # Usando la variable de entorno DB_PASSWORD
        database=os.environ.get('DB_NAME'),      # Usando la variable de entorno DB_NAME
        port=os.environ.get('DB_PORT', 3306)     # Usando la variable de entorno DB_PORT, con valor predeterminado 3306
    )

API_RENIEC_TOKEN = 'apis-token-14880.Mj8z0QRbzJsptLsh0QD0ipCEdupe34k0'

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def do_login():
    usuario = request.form['usuario']
    clave = request.form['clave']
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM usuarios WHERE username=%s AND password=%s', (usuario, clave))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user:
        session['usuario'] = usuario
        return redirect('/dashboard')
    else:
        flash('Usuario o contraseña incorrectos')
        return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect('/')
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT p.id, CONCAT(c.nombres, " ", c.apellidos) AS nombre, p.monto, p.fecha 
        FROM prestamos p JOIN clientes c ON p.cliente_id = c.id
    ''')
    prestamos = cursor.fetchall()
    cuotas = []
    if prestamos:
        cursor.execute('SELECT * FROM cuotas WHERE prestamo_id = %s', (prestamos[0]['id'],))
        cuotas = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('dashboard.html', prestamos=prestamos, cuotas=cuotas)

@app.route('/api/cuotas/<int:prestamo_id>')
def obtener_cuotas(prestamo_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT numero, fecha_pago, interes, monto FROM cuotas WHERE prestamo_id = %s', (prestamo_id,))
    cuotas = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(cuotas)

@app.route('/api/reniec', methods=['GET'])
def consultar_reniec():
    dni = request.args.get('dni')
    if not dni:
        return {'error': 'DNI requerido'}, 400

    headers = {
        'Authorization': f'Bearer {API_RENIEC_TOKEN}'
    }
    url = f'https://api.apis.net.pe/v2/reniec/dni?numero={dni}'
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        return {'error': 'No se pudo consultar'}, response.status_code

@app.route('/api/sunat', methods=['GET'])
def consultar_ruc():
    ruc = request.args.get('ruc')
    if not ruc:
        return {'error': 'RUC requerido'}, 400

    headers = {
        'Authorization': f'Bearer {API_RENIEC_TOKEN}'
    }
    url = f'https://api.apis.net.pe/v2/sunat/ruc?numero={ruc}'
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        return {'error': 'No se pudo consultar'}, response.status_code

@app.route('/cambiar_contrasena', methods=['GET', 'POST'])
def cambiar_contrasena():
    if 'usuario' not in session:
        return redirect('/')
    if request.method == 'POST':
        actual = request.form['actual']
        nueva = request.form['nueva']
        confirmar = request.form['confirmar']
        if nueva != confirmar:
            flash('La nueva contraseña no coincide con la confirmación')
            return redirect('/cambiar_contrasena')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE username=%s AND password=%s', (session['usuario'], actual))
        if cursor.fetchone():
            cursor.execute('UPDATE usuarios SET password=%s WHERE username=%s', (nueva, session['usuario']))
            conn.commit()
            flash('Contraseña actualizada correctamente')
        else:
            flash('Contraseña actual incorrecta')
        cursor.close()
        conn.close()
        return redirect('/cambiar_contrasena')
    return render_template('cambiar_contraseña.html')

@app.route('/descargar_pdf', methods=['POST'])
def descargar_pdf():
    prestamo_id = request.form['prestamo_id']
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('''
        SELECT p.id, p.monto, p.fecha, p.cuotas, CONCAT(c.nombres, " ", c.apellidos) AS nombre
        FROM prestamos p
        JOIN clientes c ON p.cliente_id = c.id
        WHERE p.id = %s
    ''', (prestamo_id,))
    prestamo = cursor.fetchone()

    cursor.execute('''
        SELECT numero, monto, interes, fecha_pago
        FROM cuotas
        WHERE prestamo_id = %s
    ''', (prestamo_id,))
    cuotas = cursor.fetchall()
    cursor.close()
    conn.close()

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle("Cronograma de Pago")

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(200, 750, "Cronograma de Pago")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, 720, f"Cliente: {prestamo['nombre']}")
    pdf.drawString(50, 700, f"Monto total: S/ {prestamo['monto']}")
    pdf.drawString(50, 680, f"Fecha inicio: {prestamo['fecha']}")
    pdf.drawString(50, 660, f"Nro de cuotas: {prestamo['cuotas']}")

    y = 630
    pdf.drawString(50, y, "Cuota")
    pdf.drawString(150, y, "Monto")
    pdf.drawString(250, y, "Interés")
    pdf.drawString(350, y, "Fecha Pago")
    y -= 20

    for cuota in cuotas:
        pdf.drawString(50, y, str(cuota['numero']))
        pdf.drawString(150, y, f"S/ {cuota['monto']:.2f}")
        pdf.drawString(250, y, f"{cuota['interes'] * 100:.2f} %")
        pdf.drawString(350, y, str(cuota['fecha_pago']))
        y -= 20
        if y < 100:
            pdf.showPage()
            y = 750

    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='cronograma.pdf', mimetype='application/pdf')

@app.route('/solicitar', methods=['GET', 'POST'])
def solicitar():
    if 'usuario' not in session:
        return redirect('/')

    if request.method == 'POST':
        try:
            dni = request.form['dni']
            fecha = request.form['fecha']
            fecha_primer_pago = request.form['fecha_primer_pago']
            cuotas = int(request.form['cuotas'])
            monto = float(request.form['monto'])
            tipo_fecha = request.form['tipo_fecha']

            conn = get_db()
            cursor = conn.cursor(dictionary=True)

            cursor.execute('SELECT * FROM clientes WHERE dni = %s', (dni,))
            cliente = cursor.fetchone()

            if not cliente:
                headers = {'Authorization': f'Bearer {API_RENIEC_TOKEN}'}
                reniec_url = f'https://api.apis.net.pe/v2/reniec/dni?numero={dni}'
                res = requests.get(reniec_url, headers=headers)

                if res.status_code == 200:
                    data = res.json()
                    nombres = data.get('nombres', 'Desconocido')
                    apellidos = f"{data.get('apellidoPaterno', '')} {data.get('apellidoMaterno', '')}".strip()
                else:
                    nombres = 'Cliente'
                    apellidos = 'Nuevo'

                cursor.execute(
                    'INSERT INTO clientes (dni, nombres, apellidos) VALUES (%s, %s, %s)',
                    (dni, nombres, apellidos)
                )
                conn.commit()
                cursor.execute('SELECT * FROM clientes WHERE dni = %s', (dni,))
                cliente = cursor.fetchone()

            cursor.execute(
                'INSERT INTO prestamos (cliente_id, monto, cuotas, fecha) VALUES (%s, %s, %s, %s)',
                (cliente['id'], monto, cuotas, fecha)
            )
            conn.commit()
            cursor.execute('SELECT LAST_INSERT_ID() AS id')
            prestamo_id = cursor.fetchone()['id']

            fecha_inicial = datetime.strptime(fecha_primer_pago, "%Y-%m-%d")
            monto_cuota = round(monto / cuotas, 2)
            tasa_interes = 0.05
            interes_cuota = round(monto_cuota * tasa_interes, 2)

            for i in range(1, cuotas + 1):
                if tipo_fecha == '30dias':
                    fecha_pago = fecha_inicial + timedelta(days=30 * (i - 1))
                else:
                    fecha_pago = (fecha_inicial.replace(day=1) + timedelta(days=32*(i-1))).replace(day=fecha_inicial.day)

                cursor.execute(
                    'INSERT INTO cuotas (prestamo_id, numero, monto, fecha_pago, interes, pagado) VALUES (%s, %s, %s, %s, %s, 0)',
                    (prestamo_id, i, monto_cuota, fecha_pago.date(), interes_cuota)
                )

            conn.commit()
            cursor.close()
            conn.close()

            return redirect('/dashboard')
        except Exception as e:
            flash(f'Error al registrar el préstamo: {e}')
            return redirect('/solicitar')

    return render_template('solicitar_prestamo.html')

if __name__ == '__main__':
    app.run(debug=True)
