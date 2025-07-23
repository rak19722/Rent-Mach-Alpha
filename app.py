from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime  # Esto importa la clase datetime del módulo datetime
import datetime as dt  # Esto importa el módulo completo con un alias
from sqlalchemy.ext.mutable import MutableDict
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer



# --------------------- Configuración de la App ---------------------
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rentmatch.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# --------------------- Modelos de Base de Datos ---------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)  # Cambiado a nullable
    password = db.Column(db.String(200), nullable=True)
    role = db.Column(db.String(20), nullable=False)
    verified = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Float, default=0.0)
    is_external = db.Column(db.Boolean, default=False)  # Nuevo campo
    external_creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Quién creó el perfil
    external_creator = db.relationship('User', remote_side=[id], foreign_keys=[external_creator_id])
    external_name = db.Column(db.String(100), nullable=True)
    reviews_received = db.relationship('Review', foreign_keys='Review.reviewed_id', backref='user_received', lazy='dynamic')
    reviews_given = db.relationship('Review', foreign_keys='Review.reviewer_id', backref='user_given', lazy='dynamic')
    document_requirements = db.Column(db.JSON, default=list)

def is_landlord(self):
        return self.role == 'landlord'

def is_tenant(self):
        return self.role == 'tenant'

# Configuración del servidor de correo
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'rak19722@gmail.com'
app.config['MAIL_PASSWORD'] = 'dhyk hpxx zgpk buqe'
app.config['MAIL_DEFAULT_SENDER'] = 'rak19722@gmail.com'

mail = Mail(app)

def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='email-confirm')

def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=expiration)
    except:
        return False
    return email

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    bedrooms = db.Column(db.Integer, nullable=False)
    bathrooms = db.Column(db.Integer, nullable=False)
    area = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    pet_friendly = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    available = db.Column(db.Boolean, default=True)
    images = db.relationship('PropertyImage', backref='property', cascade="all, delete-orphan")

class PropertyImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reviewed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Float, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    role_reviewed = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reply = db.Column(db.Text)
    reply_date = db.Column(db.DateTime)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id', ondelete='SET NULL'))  # Cambiado aquí
    anonymous = db.Column(db.Boolean, default=False)
    had_rental = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    
    # Relaciones
    reviewer = db.relationship('User', foreign_keys=[reviewer_id])
    reviewed = db.relationship('User', foreign_keys=[reviewed_id])
    property = db.relationship('Property')  # Esta relación permanece igual

    helpful_votes = db.Column(db.Integer, default=0)
    voters = db.Column(db.JSON, default=[])

class TenantRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    landlord_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected, finalized
    stage = db.Column(db.Integer, default=0)  # 0: solicitud, 1: documentos, 2: contactos
    documents = db.Column(MutableDict.as_mutable(db.JSON))
    contact_shared = db.Column(db.Boolean, default=False)  # Nuevo campo
    finalized = db.Column(db.Boolean, default=False)  # Nuevo campo
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tenant = db.relationship('User', foreign_keys=[tenant_id], backref='requests_sent')
    landlord = db.relationship('User', foreign_keys=[landlord_id], backref='requests_received')
    property = db.relationship('Property')


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    relation_id = db.Column(db.Integer, db.ForeignKey('tenant_request.id'), nullable=False)
    image_path = db.Column(db.String(300), nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.String(300))

    relation = db.relationship('TenantRequest', backref='payments')
    uploaded_by = db.relationship('User')

    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Agrega esto
    amount = db.Column(db.Float)  # Campo opcional para el monto


# --------------------- Rutas Principales ---------------------
@app.route('/')
def index():
    # Obtener IDs de propiedades con arrendamientos finalizados
    finalized_properties_ids = [r.property_id for r in 
                              TenantRequest.query.filter_by(status='finalized').all()]
    
    # Consulta original con el filtro adicional
    properties = Property.query.filter_by(available=True)\
                              .filter(~Property.id.in_(finalized_properties_ids))\
                              .limit(6)\
                              .all()
    
    return render_template('index.html', properties=properties)

@app.route('/properties')
def properties():
    location = request.args.get('location', '')
    min_price = request.args.get('min_price', 0)
    max_price = request.args.get('max_price', 100000)
    bedrooms = request.args.get('bedrooms', 0)
    property_type = request.args.get('type', '')
    page = request.args.get('page', 1, type=int)
    per_page = 12  # Propiedades por página

    # Obtener IDs de propiedades con arrendamientos finalizados
    finalized_properties_ids = [r.property_id for r in 
                              TenantRequest.query.filter_by(status='finalized').all()]

    query = Property.query.filter_by(available=True).filter(~Property.id.in_(finalized_properties_ids))
    
    if location:
        query = query.filter(Property.location.contains(location))
    if min_price:
        query = query.filter(Property.price >= float(min_price))
    if max_price:
        query = query.filter(Property.price <= float(max_price))
    if bedrooms:
        query = query.filter(Property.bedrooms >= int(bedrooms))
    if property_type:
        query = query.filter(Property.type == property_type)

    # Aplicar paginación
    properties_pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('properties.html', 
                         properties=properties_pagination.items,
                         pagination=properties_pagination,
                         location=location,
                         min_price=min_price,
                         max_price=max_price,
                         bedrooms=bedrooms,
                         property_type=property_type)

@app.route('/property/<int:id>', methods=['GET'])
def property_detail(id):
    property = Property.query.get_or_404(id)
    landlord = User.query.get(property.user_id)
    
    # Verificar si la propiedad tiene un arrendamiento finalizado
    is_finalized = TenantRequest.query.filter_by(
        property_id=id,
        status='finalized'
    ).first() is not None
    
    # Si está finalizada y el usuario no es ni arrendador ni inquilino, redirigir
    if is_finalized:
        if 'user_id' not in session or (session['user_id'] != landlord.id and 
                                      session['user_id'] not in [r.tenant_id for r in 
                                      TenantRequest.query.filter_by(
                                          property_id=id,
                                          status='finalized'
                                      ).all()]):
            flash('Esta propiedad ya no está disponible')
            return redirect(url_for('properties'))
    
    existing_request = None
    if 'user_id' in session and session['role'] == 'tenant':
        existing_request = TenantRequest.query.filter_by(
            tenant_id=session['user_id'],
            property_id=id
        ).first()
        
    return render_template('property_detail.html', 
                         property=property, 
                         landlord=landlord, 
                         existing_request=existing_request)


from datetime import datetime

@app.template_filter('format_datetime')
def format_datetime(value, format='%d/%m/%Y %H:%M'):
    if not value:
        return ""
    
    # Si ya es un objeto datetime
    if hasattr(value, 'strftime'):
        return value.strftime(format)
    
    # Si es un string ISO
    try:
        dt_obj = datetime.fromisoformat(value)
        return dt_obj.strftime(format)
    except (ValueError, TypeError):
        return str(value)  # Fallback: devuelve el valor original como string
    

@app.route('/request_interest/<int:property_id>', methods=['POST'])
def request_interest(property_id):
    if 'user_id' not in session or session['role'] != 'tenant':
        return redirect(url_for('login'))

    property = Property.query.get_or_404(property_id)
    landlord_id = property.user_id  # El arrendador es el dueño de la propiedad
    
    # Verificar si ya existe una solicitud
    existing = TenantRequest.query.filter_by(
        tenant_id=session['user_id'],
        property_id=property_id
    ).first()
    
    if existing:
        flash('Ya has enviado una solicitud para esta propiedad.')
        return redirect(url_for('property_detail', id=property_id))

    # Crear nueva solicitud
    new_request = TenantRequest(
        tenant_id=session['user_id'],
        landlord_id=landlord_id,  # Asegúrate que esto sea correcto
        property_id=property_id,
        status='pending',
        stage=0
    )
    
    db.session.add(new_request)
    db.session.commit()
    flash('Solicitud enviada al arrendador.')
    return redirect(url_for('property_detail', id=property_id))


@app.route('/manage_request/<int:request_id>', methods=['POST'])
def manage_request(request_id):
    action = request.form.get('action')
    request_obj = TenantRequest.query.get_or_404(request_id)
    
    if 'user_id' not in session or session['user_id'] != request_obj.landlord_id:
        flash("No autorizado.")
        return redirect(url_for('dashboard'))

    if action == 'accept':
        request_obj.status = 'accepted'
        request_obj.stage = 1  # Etapa 1: revisión de reputación pasada
    elif action == 'reject':
        request_obj.status = 'rejected'

    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/advance_stage/<int:request_id>', methods=['POST'])
def advance_stage(request_id):
    req = TenantRequest.query.get_or_404(request_id)
    
    if 'user_id' not in session or session['user_id'] != req.landlord_id:
        flash("No autorizado.")
        return redirect(url_for('dashboard'))

    if req.status != 'accepted':
        flash("La solicitud no está aceptada.")
        return redirect(url_for('dashboard'))

    if req.stage < 3:
        req.stage += 1
        db.session.commit()

    return redirect(url_for('dashboard'))

# Configuración adicional para documentos
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def file_exists(filepath):
    """Verifica si un archivo existe en el sistema"""
    return os.path.exists(filepath)

@app.context_processor
def utility_processor():
    """Hace disponible file_exists en todas las plantillas"""
    return dict(file_exists=file_exists)

@app.route('/upload_documents/<int:request_id>', methods=['POST'])
def upload_documents(request_id):
    req = TenantRequest.query.get_or_404(request_id)

    if 'user_id' not in session or session['user_id'] != req.tenant_id:
        flash("No autorizado.")
        return redirect(url_for('dashboard'))

    if 'documents' not in request.files:
        flash('No se seleccionaron archivos')
        return redirect(url_for('process_request', request_id=request_id))

    uploaded_files = request.files.getlist('documents')
    if not uploaded_files or not any(f.filename for f in uploaded_files):
        flash('No se seleccionaron archivos válidos')
        return redirect(url_for('process_request', request_id=request_id))

    # Inicializar documentos si no existen
    if req.documents is None:
        req.documents = {}

    for file in uploaded_files:
        if file and file.filename:
            # Validar tipo de archivo
            if not allowed_file(file.filename):
                flash(f'El archivo {file.filename} tiene un formato no permitido')
                continue

            # Validar tamaño
            file.seek(0, os.SEEK_END)
            file_length = file.tell()
            file.seek(0)
            if file_length > MAX_FILE_SIZE:
                flash(f'El archivo {file.filename} excede el tamaño máximo de 5MB')
                continue

            filename = secure_filename(file.filename)
            unique_name = f"{uuid.uuid4().hex}_{filename}"
            path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            
            try:
                file.save(path)
                
                # Guardar metadatos del documento
                # En tu ruta upload_documents
                doc_data = {
                    'path': f"uploads/{unique_name}",
                    'filename': filename,
                    'uploaded_at': datetime.utcnow().isoformat(),  # Guarda como string ISO
                    'size': file_length
                }
                
                # Usar el nombre original como clave (puedes cambiarlo por un ID si prefieres)
                req.documents[filename] = doc_data
                
            except Exception as e:
                app.logger.error(f"Error al guardar archivo {filename}: {str(e)}")
                flash(f'Error al guardar {filename}')

    db.session.commit()
    flash("Documentos subidos correctamente." if len(uploaded_files) > 1 else "Documento subido correctamente.")
    return redirect(url_for('process_request', request_id=request_id))

@app.route('/remove_document/<int:request_id>', methods=['POST'])
def remove_document(request_id):
    req = TenantRequest.query.get_or_404(request_id)
    
    if 'user_id' not in session or session['user_id'] != req.tenant_id:
        flash("No autorizado", "error")
        return redirect(url_for('dashboard'))

    doc_name = request.form.get('doc_name')
    
    if not req.documents or doc_name not in req.documents:
        flash("Documento no encontrado", "error")
        return redirect(url_for('process_request', request_id=request_id))

    # Eliminar archivo físico
    doc_data = req.documents[doc_name]
    try:
        if doc_data.get('path'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], doc_data['path'].split('/')[-1])
            if os.path.exists(file_path):
                os.remove(file_path)
    except Exception as e:
        app.logger.error(f"Error eliminando archivo: {str(e)}")
        flash("Error al eliminar el archivo físico", "error")

    # Eliminar de la base de datos
    try:
        del req.documents[doc_name]
        db.session.commit()
        flash("Documento eliminado correctamente", "success")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error actualizando BD: {str(e)}")
        flash("Error al actualizar la base de datos", "error")

    return redirect(url_for('process_request', request_id=request_id))

@app.route('/handle_interest/<int:request_id>', methods=['POST'])
def handle_interest(request_id):
    req = TenantRequest.query.get_or_404(request_id)
    
    if 'user_id' not in session or session['user_id'] != req.landlord_id:
        flash("No autorizado.")
        return redirect(url_for('dashboard'))

    action = request.form.get('action')
    
    if action == 'accept':
        req.status = 'accepted'
        req.stage = 1  # Pasar a etapa 1 (revisión de reputación)
        flash("Solicitud aceptada. Ahora en etapa de revisión de reputación.")
    elif action == 'reject':
        req.status = 'rejected'
        flash("Solicitud rechazada.")
    elif action == 'next_stage' and req.status == 'accepted' and req.stage < 3:
        req.stage += 1
        flash(f"Solicitud avanzada a etapa {req.stage}.")
    else:
        flash("Acción no válida.")

    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/final_decision/<int:request_id>', methods=['POST'])
def final_decision(request_id):
    req = TenantRequest.query.get_or_404(request_id)

    if 'user_id' not in session or session['user_id'] != req.tenant_id:
        flash("No autorizado.")
        return redirect(url_for('dashboard'))

    if req.stage != 3 or req.status != 'accepted':
        flash("No puedes tomar esta decisión aún.")
        return redirect(url_for('dashboard'))

    action = request.form.get('action')
    if action == 'accept':
        req.status = 'contract_finalized'
        flash("Has aceptado el contrato. Contacto exitoso.")
    elif action == 'reject':
        req.status = 'rejected'
        flash("Has rechazado el contrato.")
    else:
        flash("Acción inválida.")

    db.session.commit()
    return redirect(url_for('dashboard'))

from datetime import datetime  # Asegúrate que está importado al inicio del archivo

@app.route('/process/<int:request_id>')
def process_request(request_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    req = TenantRequest.query.get_or_404(request_id)
    
    # Verificar permisos
    if session['user_id'] not in [req.tenant_id, req.landlord_id]:
        flash("No tienes permiso para ver este proceso.")
        return redirect(url_for('dashboard'))
    
    property = Property.query.get(req.property_id)
    landlord = User.query.get(req.landlord_id)
    tenant = User.query.get(req.tenant_id)
    
    return render_template('process.html',
                         request=req,
                         property=property,
                         landlord=landlord,
                         tenant=tenant,
                         user=User.query.get(session['user_id']),
                         datetime=datetime)  # Pasar datetime al template

# Agrega esto cerca de donde configuras tu aplicación Flask (al inicio del archivo)
@app.template_filter('number_format')
def number_format(value, decimals=0):
    """Formatea un número con separadores de miles y decimales opcionales"""
    if value is None:
        return ""
    try:
        return "{:,.{}f}".format(float(value), decimals).replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(value)
    
@app.route('/configure_documents', methods=['GET', 'POST'])
def configure_documents():
    if 'user_id' not in session or session['role'] != 'landlord':
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        titles = request.form.getlist('document_titles')
        descriptions = request.form.getlist('document_descriptions')
        
        # Crear nueva lista de documentos
        new_requirements = []
        for title, desc in zip(titles, descriptions):
            if title.strip():  # Solo agregar si tiene título
                new_requirements.append({
                    'title': title.strip(),
                    'description': desc.strip()
                })
        
        # Actualizar los requisitos del usuario
        user.document_requirements = new_requirements
        db.session.commit()
        flash('Configuración de documentos guardada exitosamente', 'success')
        return redirect(url_for('dashboard'))
    
    # Para GET, mostrar el formulario con los requisitos actuales
    return render_template('configure_documents.html', current_user=user)

@app.route('/approve_documents/<int:request_id>', methods=['POST'])
def approve_documents(request_id):
    req = TenantRequest.query.get_or_404(request_id)
    if 'user_id' not in session or session['user_id'] != req.landlord_id:
        flash("No autorizado")
        return redirect(url_for('dashboard'))
    
    req.stage = 2  # Avanzar a etapa de contacto
    db.session.commit()
    flash("Documentos aprobados. Proceder a etapa de contacto.")
    return redirect(url_for('process_request', request_id=request_id))

@app.route('/share_contacts/<int:request_id>', methods=['POST'])
def share_contacts(request_id):
    req = TenantRequest.query.get_or_404(request_id)
    if 'user_id' not in session or session['user_id'] != req.tenant_id:
        flash("No autorizado")
        return redirect(url_for('dashboard'))
    
    req.contact_shared = True
    db.session.commit()
    flash("Tus datos de contacto han sido compartidos con el arrendador.")
    return redirect(url_for('process_request', request_id=request_id))

@app.route('/finalize_contract/<int:request_id>', methods=['POST'])
def finalize_contract(request_id):
    req = TenantRequest.query.get_or_404(request_id)
    
    if 'user_id' not in session or session['user_id'] != req.landlord_id:
        flash("No autorizado", "error")
        return redirect(url_for('dashboard'))

    try:
        # Marcar como finalizado
        req.finalized = True
        req.status = 'finalized'
        req.stage = 4  # Asegúrate de que esta etapa existe en tu lógica
        
        # Marcar la propiedad como no disponible
        property = Property.query.get(req.property_id)
        if property:
            property.available = False
        
        db.session.commit()
        flash("Contrato finalizado exitosamente!", "success")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error al finalizar contrato: {str(e)}")
        flash("Ocurrió un error al finalizar el contrato", "error")
    
    return redirect(url_for('process_request', request_id=request_id))


@app.route('/cancel_lease/<int:request_id>', methods=['POST'])
def cancel_lease(request_id):
    if 'user_id' not in session:
        flash("Debes iniciar sesión para realizar esta acción.")
        return redirect(url_for('login'))

    lease = TenantRequest.query.get_or_404(request_id)
    user_id = session['user_id']

    if user_id not in [lease.tenant_id, lease.landlord_id]:
        flash("No tienes permiso para cancelar este contrato.")
        return redirect(url_for('dashboard'))

    cancellable_states = ['accepted', 'contract_finalized', 'finalized']
    
    if lease.status not in cancellable_states:
        flash("Este contrato no puede ser cancelado en su estado actual.")
        return redirect(url_for('dashboard'))

    try:
        lease.status = 'canceled'
        lease.finalized = True
        
        for payment in lease.payments:
            if payment.status == 'pending':
                payment.status = 'canceled'
                payment.note = f"Cancelado por cancelación de contrato (Usuario {user_id})"
        
        property = lease.property
        property.available = True
        
        # NO eliminamos reseñas asociadas al contrato
        db.session.commit()
        
        flash("Contrato cancelado exitosamente.")
        return redirect(url_for('dashboard'))
    
    except Exception as e:
        db.session.rollback()
        flash(f"Error al cancelar el contrato: {str(e)}")
        return redirect(url_for('dashboard'))


@app.route('/payment_history')
def payment_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get(user_id)
    role = user.role

    if role == 'landlord':
        relations = TenantRequest.query.filter(
            TenantRequest.landlord_id == user_id,
            TenantRequest.finalized == True
        ).all()
    else:
        relations = TenantRequest.query.filter(
            TenantRequest.tenant_id == user_id,
            TenantRequest.finalized == True
        ).all()

    return render_template("payment_history.html", 
                         user=user,
                         active_rentals=relations,  # Cambiado de relations a active_rentals
                         role=role)

@app.route('/upload_payment/<int:request_id>', methods=['POST'])
def upload_payment(request_id):
    req = TenantRequest.query.get_or_404(request_id)
    
    if 'user_id' not in session or session['user_id'] != req.tenant_id:
        flash("No autorizado.", "error")
        return redirect(url_for('payment_history'))

    file = request.files.get('payment_image')
    if not file or file.filename == '':
        flash("No se seleccionó ningún archivo.", "error")
        return redirect(url_for('payment_history'))

    # Validar tipo de archivo
    if not allowed_file(file.filename):
        flash("Formato de archivo no permitido. Solo se aceptan JPG, PNG.", "error")
        return redirect(url_for('payment_history'))

    # Validar tamaño del archivo (5MB máximo)
    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    file.seek(0)
    if file_length > 5 * 1024 * 1024:  # 5MB
        flash("El archivo es demasiado grande. Máximo 5MB.", "error")
        return redirect(url_for('payment_history'))

    # Guardar archivo
    filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    
    try:
        file.save(filepath)
    except Exception as e:
        app.logger.error(f"Error al guardar archivo: {str(e)}")
        flash("Error al guardar el comprobante.", "error")
        return redirect(url_for('payment_history'))

    # Crear registro de pago
    new_payment = Payment(
        relation_id=req.id,
        image_path=f'uploads/{unique_name}',
        uploaded_by_id=session['user_id'],
        status='pending',
        note=request.form.get('note'),
        amount=float(request.form.get('amount')) if request.form.get('amount') else None
    )

    try:
        db.session.add(new_payment)
        db.session.commit()
        flash("Comprobante de pago subido correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error al guardar pago en BD: {str(e)}")
        flash("Error al registrar el pago en el sistema.", "error")

    return redirect(url_for('payment_history'))


@app.route('/update_payment_status/<int:payment_id>', methods=['POST'])
def update_payment_status(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    
    if 'user_id' not in session or session['user_id'] != payment.relation.landlord_id:
        flash("No autorizado.", "error")
        return redirect(url_for('payment_history'))

    action = request.form.get('action')
    if action not in ['approve', 'reject']:
        flash("Acción no válida.", "error")
        return redirect(url_for('payment_history'))

    payment.status = 'approved' if action == 'approve' else 'rejected'
    
    try:
        db.session.commit()
        flash(f"Pago {payment.status} correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error al actualizar estado de pago: {str(e)}")
        flash("Error al actualizar el estado del pago.", "error")

    return redirect(url_for('payment_history'))


# --------------------- Autenticación ---------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            if not user.verified:
                return render_template('login.html', error='Debes verificar tu correo electrónico antes de iniciar sesión.')
            
            # Usuario autenticado y verificado
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            return redirect(url_for('dashboard'))

        return render_template('login.html', error='Credenciales incorrectas')

    return render_template('login.html')




@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Obtener datos del formulario
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', '').strip()
        terms_accepted = request.form.get('terms')

        # Validaciones básicas
        if not all([username, email, password, role]):
            return render_template('register.html',
                                   error='Todos los campos son obligatorios.',
                                   username=username,
                                   email=email)

        if not terms_accepted:
            return render_template('register.html',
                                   error='Debes aceptar los términos y condiciones.',
                                   username=username,
                                   email=email)

        # Validar formato de email
        if '@' not in email or '.' not in email.split('@')[-1]:
            return render_template('register.html',
                                   error='Por favor ingresa un email válido.',
                                   username=username,
                                   email=email)

        # Verificar unicidad de email y username
        if User.query.filter_by(email=email).first():
            return render_template('register.html',
                                   error='El correo electrónico ya está registrado.',
                                   username=username)

        if User.query.filter_by(username=username).first():
            return render_template('register.html',
                                   error='El nombre de usuario ya está en uso.',
                                   email=email)

        # Validar fortaleza de contraseña
        if len(password) < 8:
            return render_template('register.html',
                                   error='La contraseña debe tener al menos 8 caracteres.',
                                   username=username,
                                   email=email)

        # Crear nuevo usuario (no verificado)
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            role=role,
            verified=False
        )

        db.session.add(new_user)
        db.session.commit()

        # Generar y enviar token de confirmación
        token = generate_confirmation_token(email)
        confirm_url = url_for('confirm_email', token=token, _external=True)

        html = render_template('email_confirmation.html', confirm_url=confirm_url)
        subject = "Confirma tu cuenta en RentMatch"
        msg = Message(subject=subject, recipients=[email], html=html)
        mail.send(msg)

        flash('Te has registrado correctamente. Revisa tu correo para confirmar tu cuenta antes de iniciar sesión.', 'info')
        return redirect(url_for('login'))

    # Si es GET, mostrar formulario vacío
    return render_template('register.html')





#confirmacion correo
@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = confirm_token(token)
    except:
        flash('El enlace de confirmación es inválido o ha expirado.', 'error')
        return redirect(url_for('login'))

    user = User.query.filter_by(email=email).first_or_404()
    if user.verified:
        flash('Cuenta ya confirmada. Inicia sesión.', 'info')
    else:
        user.verified = True
        db.session.commit()
        flash('Gracias por confirmar tu cuenta. Ahora puedes iniciar sesión.', 'success')

    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    recent_reviews = Review.query.filter_by(reviewed_id=user.id)\
                               .order_by(Review.created_at.desc())\
                               .limit(3).all()

    if user.role == 'landlord':
        received_requests = TenantRequest.query.filter_by(
            landlord_id=user.id
        ).order_by(TenantRequest.created_at.desc()).all()
        
        # Mostrar TODAS las propiedades del arrendador, incluyendo las finalizadas
        properties = Property.query.filter_by(user_id=user.id).all()

        return render_template('dashboard.html',
                             user=user,
                             properties=properties,
                             recent_reviews=recent_reviews,
                             received_requests=received_requests)
    else:
        favorites = Favorite.query.filter_by(user_id=user.id).all()
        favorite_properties = [Property.query.get(f.property_id) for f in favorites]
        sent_requests = TenantRequest.query.filter_by(tenant_id=user.id).all()

        # Para inquilinos, mostrar propiedades de sus solicitudes finalizadas
        finalized_properties = []
        for req in sent_requests:
            if req.status == 'finalized':
                prop = Property.query.get(req.property_id)
                if prop:
                    finalized_properties.append(prop)

        return render_template('dashboard.html',
                             user=user,
                             favorites=favorite_properties,
                             recent_reviews=recent_reviews,
                             sent_requests=sent_requests,
                             finalized_properties=finalized_properties)

# --------------------- Propiedades ---------------------
@app.route('/create_property', methods=['GET', 'POST'])
def create_property():
    if 'user_id' not in session or session.get('role') != 'landlord':
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            # Validación de datos básicos
            title = request.form.get('title', '').strip()
            if not title:
                flash('El título es requerido')
                return redirect(request.url)
                
            description = request.form.get('description', '').strip()
            price = float(request.form.get('price', 0))
            location = request.form.get('location', '').strip()
            bedrooms = int(request.form.get('bedrooms', 0))
            bathrooms = int(request.form.get('bathrooms', 0))
            area = float(request.form.get('area', 0))
            property_type = request.form.get('type', '')
            pet_friendly = request.form.get('pet_friendly') == 'on'
            
            images = request.files.getlist('images')
            if not images or not any(img.filename for img in images):
                flash('Debes subir al menos una imagen')
                return redirect(request.url)
                
            if len(images) > 10:
                flash('Solo se permiten hasta 10 imágenes.')
                return redirect(request.url)

            # Crear la propiedad en una sola transacción
            new_property = Property(
                title=title,
                description=description,
                price=price,
                location=location,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                area=area,
                type=property_type,
                pet_friendly=pet_friendly,
                user_id=session['user_id'],
            )
            db.session.add(new_property)
            db.session.flush()  # Asigna un ID sin hacer commit

            # Procesar imágenes
            for file in images:
                if file and file.filename:
                    # Verificar que es una imagen (por extensión)
                    filename = secure_filename(file.filename)
                    if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        continue
                        
                    unique_name = f"{uuid.uuid4().hex}_{filename}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                    
                    # Asegurar que el directorio existe
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                    
                    file.save(filepath)
                    image = PropertyImage(filename=unique_name, property_id=new_property.id)
                    db.session.add(image)

            db.session.commit()
            flash('Propiedad creada con éxito.')
            return redirect(url_for('dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la propiedad: {str(e)}')
            return redirect(request.url)

    return render_template('property_form.html')

@app.route('/edit_property/<int:id>', methods=['GET', 'POST'])
def edit_property(id):
    if 'user_id' not in session or session.get('role') != 'landlord':
        return redirect(url_for('login'))

    property = Property.query.get_or_404(id)
    if property.user_id != session['user_id']:
        flash('No tienes permiso para editar esta propiedad')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            # Actualizar propiedades básicas
            property.title = request.form.get('title', '').strip()
            property.description = request.form.get('description', '').strip()
            property.price = float(request.form.get('price', 0))
            property.location = request.form.get('location', '').strip()
            property.bedrooms = int(request.form.get('bedrooms', 0))
            property.bathrooms = int(request.form.get('bathrooms', 0))
            property.area = float(request.form.get('area', 0))
            property.type = request.form.get('type', '')
            property.pet_friendly = request.form.get('pet_friendly') == 'on'
            
            # Manejo de imágenes (ahora usando 'images' en lugar de 'new_images')
            images = request.files.getlist('images')
            
            if images and any(img.filename for img in images):
                if len(images) > 10:
                    flash('Solo se permiten hasta 10 imágenes nuevas.')
                    return redirect(request.url)
                    
                for file in images:
                    if file and file.filename:
                        filename = secure_filename(file.filename)
                        if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                            continue
                            
                        unique_name = f"{uuid.uuid4().hex}_{filename}"
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                        
                        # Asegurar que el directorio existe
                        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                        
                        file.save(filepath)
                        image = PropertyImage(filename=unique_name, property_id=property.id)
                        db.session.add(image)

            db.session.commit()
            flash('Propiedad actualizada con éxito.')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la propiedad: {str(e)}')
            return redirect(request.url)

    return render_template('edit_property.html', property=property)

@app.route('/delete_image/<int:id>')
def delete_image(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    image = PropertyImage.query.get_or_404(id)
    property = Property.query.get_or_404(image.property_id)
    
    if property.user_id != session['user_id']:
        flash('No tienes permiso para eliminar esta imagen')
        return redirect(url_for('dashboard'))
    
    # Eliminar archivo físico
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image.filename))
    except OSError:
        pass
    
    db.session.delete(image)
    db.session.commit()
    flash('Imagen eliminada')
    return redirect(url_for('edit_property', id=property.id))

@app.route('/delete_property/<int:property_id>', methods=['POST'])
def delete_property(property_id):
    if 'user_id' not in session:
        flash("Debes iniciar sesión para realizar esta acción.")
        return redirect(url_for('login'))

    property_to_delete = Property.query.get_or_404(property_id)
    
    if session['user_id'] != property_to_delete.user_id:
        flash("No tienes permiso para borrar esta propiedad.")
        return redirect(url_for('dashboard'))

    active_leases = TenantRequest.query.filter(
        TenantRequest.property_id == property_id,
        TenantRequest.status.in_(['accepted', 'contract_finalized', 'finalized'])
    ).first()

    if active_leases:
        flash("No puedes borrar esta propiedad porque tiene arrendamientos activos o confirmados.")
        return redirect(url_for('property_detail', id=property_id))

    try:
        # Eliminar favoritos asociados
        Favorite.query.filter_by(property_id=property_id).delete()
        
        # Eliminar pagos asociados
        Payment.query.filter(Payment.relation.has(property_id=property_id)).delete()
        
        # Eliminar solicitudes asociadas
        TenantRequest.query.filter_by(property_id=property_id).delete()
        
        # NO eliminamos las reviews asociadas, solo las desvinculamos
        Review.query.filter_by(property_id=property_id).update({'property_id': None})
        
        # Finalmente, eliminar la propiedad
        db.session.delete(property_to_delete)
        db.session.commit()
        
        flash("Propiedad eliminada exitosamente.")
        return redirect(url_for('dashboard'))
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar la propiedad: {str(e)}")
        return redirect(url_for('property_detail', id=property_id))

# --------------------- Favoritos ---------------------
@app.route('/api/add_favorite', methods=['POST'])
def add_favorite():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
    property_id = request.json.get('property_id')
    existing = Favorite.query.filter_by(user_id=session['user_id'], property_id=property_id).first()
    if existing:
        return jsonify({'success': False, 'error': 'Already favorited'})
    new_favorite = Favorite(user_id=session['user_id'], property_id=property_id)
    db.session.add(new_favorite)
    db.session.commit()
    return jsonify({'success': True})

# --------------------- Reputación / Reviews ---------------------

@app.template_filter('registration_date')
def registration_date_filter(user_id):
    user = User.query.get(user_id)
    if user:
        # Asumiendo que tienes un campo date_created en tu modelo User
        return user.date_created.strftime('%b %Y') if hasattr(user, 'date_created') else "N/A"
    return "N/A"

@app.route('/reputations', methods=['GET', 'POST'])
def reputations():
    search_query = request.form.get('search_query', '') if request.method == 'POST' else ''
    role_filter = request.form.get('role_filter', '') if request.method == 'POST' else request.args.get('role_filter', '')
    rating_filter = request.form.get('rating_filter', '') if request.method == 'POST' else request.args.get('rating_filter', '')

    # Consulta base que incluye usuarios y perfiles externos
    query = User.query

    # Aplicar filtros
    if search_query:
        query = query.filter(
            db.or_(
                User.username.ilike(f'%{search_query}%'),
                User.external_name.ilike(f'%{search_query}%')
            )
        )
    
    if role_filter:
        query = query.filter(User.role == role_filter)
    
    if rating_filter:
        query = query.filter(User.rating >= float(rating_filter))

    users = query.order_by(User.rating.desc()).limit(50).all()

    # Obtener datos para secciones destacadas (solo si no hay búsqueda)
    top_landlords = []
    recent_reviews = []
    
    if not search_query:
        top_landlords = User.query.filter_by(role='landlord')\
                                .order_by(User.rating.desc())\
                                .limit(5)\
                                .all()
        
        recent_reviews = db.session.query(Review)\
                                 .order_by(Review.created_at.desc())\
                                 .limit(5)\
                                 .all()

    return render_template('reputations.html',
                         users=users,
                         search_query=search_query,
                         top_landlords=top_landlords,
                         recent_reviews=recent_reviews,
                         Review=Review)

@app.route('/submit_review', methods=['POST'])
def submit_review():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Debes iniciar sesión para dejar una opinión'}), 401

    try:
        # Obtener datos del formulario
        reviewed_id = request.form.get('reviewed_id')
        rating = request.form.get('rating')
        comment = request.form.get('comment', '').strip()
        role_reviewed = request.form.get('role_reviewed')
        anonymous = request.form.get('anonymous', 'off') == 'on'
        property_id = request.form.get('property_id', None)

        # Validaciones básicas
        if not reviewed_id or not rating or not role_reviewed:
            return jsonify({'success': False, 'error': 'Los campos marcados con * son obligatorios'}), 400

        if int(reviewed_id) == session['user_id']:
            return jsonify({'success': False, 'error': 'No puedes calificarte a ti mismo'}), 400

        # Convertir rating a float
        try:
            rating = float(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            return jsonify({'success': False, 'error': 'La calificación debe ser un número entre 1 y 5'}), 400

        # Verificar si tuvieron arriendos
        had_rental = TenantRequest.query.filter(
        ((TenantRequest.tenant_id == session['user_id']) & 
         (TenantRequest.landlord_id == reviewed_id)) |
        ((TenantRequest.landlord_id == session['user_id']) & 
         (TenantRequest.tenant_id == reviewed_id)),
        TenantRequest.status.in_(['accepted', 'contract_finalized', 'finalized', 'canceled'])
    ).first() is not None

        # Crear review
        new_review = Review(
            reviewer_id=session['user_id'],
            reviewed_id=reviewed_id,
            rating=rating,
            comment=comment,
            role_reviewed=role_reviewed,
            anonymous=anonymous,
            property_id=property_id,
            had_rental=had_rental,
            is_verified=had_rental
        )
        
        db.session.add(new_review)

        # Actualizar rating del usuario
        user = User.query.get(reviewed_id)
        if user:
            avg_rating = db.session.query(db.func.avg(Review.rating)).filter_by(reviewed_id=reviewed_id).scalar() or 0
            user.rating = round(avg_rating, 1)

        db.session.commit()
        return jsonify({
            'success': True, 
            'message': 'Tu opinión ha sido publicada',
            'review': {
                'id': new_review.id,
                'rating': new_review.rating,
                'comment': new_review.comment,
                'created_at': new_review.created_at.isoformat(),
                'is_verified': new_review.is_verified
            }
        })

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error al crear review: {str(e)}")
        return jsonify({'success': False, 'error': 'Ocurrió un error al procesar tu opinión'}), 500

# --------------------- Nuevas Rutas para Reviews ---------------------

@app.route('/api/review/reply', methods=['POST'])
def add_review_reply():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Debes iniciar sesión'})
    
    review_id = request.json.get('review_id')
    reply_text = request.json.get('reply', '').strip()
    
    review = Review.query.get_or_404(review_id)
    
    if review.reviewed_id != session['user_id']:
        return jsonify({'success': False, 'error': 'No autorizado'})
    
    review.reply = reply_text
    review.reply_date = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True, 'reply': reply_text, 'reply_date': review.reply_date.isoformat()})

@app.route('/user/<int:user_id>/reviews')
def user_reviews(user_id):
    user = User.query.get_or_404(user_id)
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Filtros
    rating_filter = request.args.get('rating')
    sort_by = request.args.get('sort', 'recent')
    
    query = Review.query.filter_by(reviewed_id=user_id)
    
    if rating_filter:
        query = query.filter(Review.rating == int(rating_filter))
    
    if sort_by == 'helpful':
        query = query.order_by(Review.was_helpful.desc())
    elif sort_by == 'verified':
        query = query.order_by(Review.is_verified.desc(), Review.created_at.desc())
    else:  # 'recent'
        query = query.order_by(Review.created_at.desc())
    
    reviews_pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    reviews = reviews_pagination.items
    
    # Cálculos estadísticos
    rating_counts = {i: 0 for i in range(1, 6)}
    for r in Review.query.filter_by(reviewed_id=user_id).all():
        rating_counts[int(r.rating)] += 1
    
    avg_rating = db.session.query(db.func.avg(Review.rating)).filter_by(reviewed_id=user_id).scalar() or 0
    total_reviews = Review.query.filter_by(reviewed_id=user_id).count()
    
    # Verificar si tuvo arriendos con el usuario actual
    had_rental = False
    tenant_requests = []
    
    if 'user_id' in session and session['user_id'] != user.id:
        tenant_requests = TenantRequest.query.filter(
            ((TenantRequest.tenant_id == session['user_id']) & 
             (TenantRequest.landlord_id == user.id)) |
            ((TenantRequest.landlord_id == session['user_id']) & 
             (TenantRequest.tenant_id == user.id)),
            TenantRequest.status == 'finalized'
        ).all()
        
        had_rental = len(tenant_requests) > 0
    
    # Cualquiera puede dejar review (sin verificación de already_reviewed)
    can_review = 'user_id' in session and session['user_id'] != user.id
    
    return render_template('user_reviews.html',
                         user=user,
                         reviews=reviews,
                         pagination=reviews_pagination,
                         avg_rating=round(avg_rating, 1),
                         rating_counts=rating_counts,
                         total_reviews=total_reviews,
                         can_review=can_review,
                         had_rental=had_rental,
                         tenant_requests=tenant_requests,
                         current_user_id=session.get('user_id'))

@app.route('/create_external_profile', methods=['GET', 'POST'])
def create_external_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        role = request.form.get('role', '').strip()
        
        if not name or not role:
            flash('Nombre y rol son obligatorios', 'error')
            return render_template('create_external_profile.html')
        
        # Crear perfil externo
        new_external = User(
            username=f"external_{uuid.uuid4().hex[:8]}",  # Nombre de usuario único
            external_name=name,
            role=role,
            is_external=True,
            external_creator_id=session['user_id'],
            verified=False,
            rating=0.0
        )
        
        db.session.add(new_external)
        db.session.commit()
        
        flash(f'Perfil externo para {name} creado exitosamente', 'success')
        return redirect(url_for('user_reviews', user_id=new_external.id))
    
    return render_template('create_external_profile.html')

# --------------------- API ---------------------
@app.route('/api/properties')
def api_properties():
    # Obtener IDs de propiedades con arrendamientos finalizados
    finalized_properties_ids = [r.property_id for r in 
                              TenantRequest.query.filter_by(status='finalized').all()]
    
    properties = Property.query.filter_by(available=True).filter(~Property.id.in_(finalized_properties_ids)).all()
    properties_data = [{
        'id': p.id,
        'title': p.title,
        'price': p.price,
        'location': p.location,
        'bedrooms': p.bedrooms,
        'type': p.type,
    } for p in properties]
    return jsonify(properties_data)


# --------------------- Run ---------------------

app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)