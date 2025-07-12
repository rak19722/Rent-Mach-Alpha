from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime

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
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    verified = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Float, default=0.0)
    reviews_received = db.relationship('Review', foreign_keys='Review.reviewed_id', backref='user_received', lazy='dynamic')
    reviews_given = db.relationship('Review', foreign_keys='Review.reviewer_id', backref='user_given', lazy='dynamic')

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
    reviewer = db.relationship('User', foreign_keys=[reviewer_id])
    reviewed = db.relationship('User', foreign_keys=[reviewed_id])

class TenantRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    landlord_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected, finalized
    stage = db.Column(db.Integer, default=0)  # 0: solicitud, 1: documentos, 2: contactos
    documents = db.Column(db.JSON)  # Cambiado de Text a JSON para mejor manejo
    contact_shared = db.Column(db.Boolean, default=False)  # Nuevo campo
    finalized = db.Column(db.Boolean, default=False)  # Nuevo campo
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tenant = db.relationship('User', foreign_keys=[tenant_id], backref='requests_sent')
    landlord = db.relationship('User', foreign_keys=[landlord_id], backref='requests_received')
    property = db.relationship('Property')

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

@app.route('/upload_documents/<int:request_id>', methods=['POST'])
def upload_documents(request_id):
    req = TenantRequest.query.get_or_404(request_id)

    if 'user_id' not in session or session['user_id'] != req.tenant_id:
        flash("No autorizado.")
        return redirect(url_for('dashboard'))

    uploaded_files = request.files.getlist("documents")
    doc_paths = {}
    for f in uploaded_files:
        if f and f.filename:
            filename = secure_filename(f.filename)
            unique_name = f"{uuid.uuid4().hex}_{filename}"
            path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            f.save(path)
            doc_paths[filename] = f"uploads/{unique_name}"  # Guardar ruta relativa

    # Convertir a JSON directamente (ya que el campo ahora es JSON)
    if req.documents:
        existing_docs = req.documents
        existing_docs.update(doc_paths)
        req.documents = existing_docs
    else:
        req.documents = doc_paths

    db.session.commit()
    flash("Documentos subidos correctamente.")
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
        flash("No autorizado")
        return redirect(url_for('dashboard'))
    
    req.finalized = True
    req.status = 'finalized'
    db.session.commit()
    flash("Contrato finalizado exitosamente!")
    return redirect(url_for('dashboard'))

@app.route('/remove_document/<int:request_id>', methods=['POST'])
def remove_document(request_id):
    req = TenantRequest.query.get_or_404(request_id)
    doc_name = request.form.get('doc_name')
    
    if 'user_id' not in session or session['user_id'] != req.tenant_id:
        flash("No autorizado")
        return redirect(url_for('dashboard'))
    
    if req.documents and doc_name in req.documents:
        # Eliminar el archivo físico
        doc_path = req.documents[doc_name]
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], doc_path.split('/')[-1]))
        except:
            pass
        
        # Eliminar de los documentos
        del req.documents[doc_name]
        db.session.commit()
        flash("Documento eliminado correctamente")
    
    return redirect(url_for('process_request', request_id=request_id))

# --------------------- Autenticación ---------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
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
                                email=email,)

        # Validar formato de email
        if '@' not in email or '.' not in email.split('@')[-1]:
            return render_template('register.html', 
                                error='Por favor ingresa un email válido.',
                                username=username,
                                email=email)

        # Validar formato de teléfono (al menos 8 dígitos)

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

        # Crear nuevo usuario
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

        # Iniciar sesión automáticamente después del registro
        session['user_id'] = new_user.id
        session['username'] = new_user.username
        session['role'] = new_user.role

        flash('¡Registro exitoso! Bienvenido a RentMatch.')
        return redirect(url_for('dashboard'))

    # Si es GET, mostrar formulario vacío
    return render_template('register.html')

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
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        price = float(request.form.get('price', 0))
        location = request.form.get('location', '').strip()
        bedrooms = int(request.form.get('bedrooms', 0))
        bathrooms = int(request.form.get('bathrooms', 0))
        area = float(request.form.get('area', 0))
        property_type = request.form.get('type', '')
        pet_friendly = True if request.form.get('pet_friendly') == 'on' else False
        images = request.files.getlist('images')

        if len(images) > 10:
            flash('Solo se permiten hasta 10 imágenes.')
            return redirect(request.url)

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
        db.session.commit()

        for file in images[:10]:
            if file and file.filename:
                filename = secure_filename(file.filename)
                unique_name = f"{uuid.uuid4().hex}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                file.save(filepath)
                image = PropertyImage(filename=unique_name, property_id=new_property.id)
                db.session.add(image)

        db.session.commit()
        flash('Propiedad creada con éxito.')
        return redirect(url_for('dashboard'))

    return render_template('create_property.html')

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
@app.route('/reputations', methods=['GET', 'POST'])
def reputations():
    if request.method == 'POST':
        search_query = request.form.get('search_query', '').strip()
        users = User.query.filter(User.username.ilike(f'%{search_query}%')).all()
        return render_template('reputations.html', users=users, search_query=search_query)

    recent_reviews = Review.query.order_by(Review.created_at.desc()).limit(5).all()
    reviewed_users = {review.reviewed_id for review in recent_reviews}
    users = User.query.filter(User.id.in_(reviewed_users)).all() if reviewed_users else []
    return render_template('reputations.html', users=users)

@app.route('/user/<int:user_id>/reviews')
def user_reviews(user_id):
    user = User.query.get_or_404(user_id)
    reviews = Review.query.filter_by(reviewed_id=user_id).order_by(Review.created_at.desc()).all()
    avg_rating = db.session.query(db.func.avg(Review.rating)).filter_by(reviewed_id=user_id).scalar() or 0
    return render_template('user_reviews.html', user=user, reviews=reviews, avg_rating=round(avg_rating, 1), current_user_id=session.get('user_id'))

@app.route('/submit_review', methods=['POST'])
def submit_review():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Debes iniciar sesión para dejar una opinión'})

    reviewed_id = request.form.get('reviewed_id')
    rating = float(request.form.get('rating'))
    comment = request.form.get('comment', '').strip()
    role_reviewed = request.form.get('role_reviewed')

    if not all([reviewed_id, rating, comment, role_reviewed]):
        return jsonify({'success': False, 'error': 'Todos los campos son obligatorios'})
    if rating < 1 or rating > 5:
        return jsonify({'success': False, 'error': 'La calificación debe ser entre 1 y 5'})
    if int(reviewed_id) == session['user_id']:
        return jsonify({'success': False, 'error': 'No puedes calificarte a ti mismo'})

    new_review = Review(
        reviewer_id=session['user_id'],
        reviewed_id=reviewed_id,
        rating=rating,
        comment=comment,
        role_reviewed=role_reviewed
    )
    db.session.add(new_review)

    user = User.query.get(reviewed_id)
    if user:
        avg_rating = db.session.query(db.func.avg(Review.rating)).filter_by(reviewed_id=reviewed_id).scalar() or 0
        user.rating = avg_rating

    db.session.commit()
    return jsonify({'success': True, 'message': 'Tu opinión ha sido publicada'})

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
