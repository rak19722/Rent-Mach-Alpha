// Manejar el menú móvil
document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuButton = document.getElementById('menu-toggle');
    const mobileMenu = document.getElementById('nav-links');

    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', function() {
            mobileMenu.classList.toggle('active');
        });
    }
});
    
    // Manejar favoritos
    document.querySelectorAll('.favorite-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const propertyId = this.dataset.propertyId;
            
            // Verificar si el usuario está logueado (se verifica mejor en el servidor)
            if (!this.classList.contains('logged-in')) {
                window.location.href = "/login";
                return;
            }
            
            // Cambiar estado visual
            this.classList.toggle('favorited');
            
            // Actualizar texto del botón
            if (this.classList.contains('favorited')) {
                this.innerHTML = '<i class="fas fa-heart"></i> Guardado';
            } else {
                this.innerHTML = '<i class="far fa-heart"></i> Guardar';
            }
            
            // Enviar petición al servidor (simulado)
            console.log(`Propiedad ${propertyId} ${this.classList.contains('favorited') ? 'añadida a' : 'eliminada de'} favoritos`);
        });
    });
    
    // Validación de formularios
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            let valid = true;
            const inputs = this.querySelectorAll('input[required], select[required]');
            
            inputs.forEach(input => {
                if (!input.value.trim()) {
                    input.style.borderColor = 'red';
                    valid = false;
                } else {
                    input.style.borderColor = '';
                }
            });
            
            if (!valid) {
                e.preventDefault();
                alert('Por favor completa todos los campos requeridos.');
            }
        });
    });
    
    // Mostrar/ocultar contraseña
   document.addEventListener("DOMContentLoaded", function () {
    const togglePassword = document.getElementById("togglePassword");
    const passwordField = document.getElementById("password");

    togglePassword.addEventListener("click", function () {
        // Cambiar el tipo de input entre 'password' y 'text'
        const isPasswordHidden = passwordField.type === "password"; // Verifica si está oculto
        passwordField.type = isPasswordHidden ? "text" : "password";

        // Alternar la clase 'active' en el ícono para reflejar el estado visual
        this.classList.toggle("active", isPasswordHidden);
    });
});

// Aquí puedes agregar cualquier comportamiento dinámico si es necesario
// Ejemplo: Cambiar las iniciales con el nombre del usuario al iniciar sesión
document.addEventListener('DOMContentLoaded', () => {
    // Cambiar las iniciales del usuario (esto depende de tu lógica backend)
    const userInitials = 'DN'; // Suponiendo que 'DN' son las iniciales del usuario
    document.getElementById('user-initials').textContent = userInitials;
});
    
    // Cargar más propiedades (simulado)
    const loadMoreBtn = document.querySelector('.load-more');
    if (loadMoreBtn) {
        loadMoreBtn.addEventListener('click', function() {
            this.textContent = 'Cargando...';
            setTimeout(() => {
                // Simular carga de más propiedades
                const propertyGrid = document.querySelector('.property-grid');
                for (let i = 0; i < 3; i++) {
                    const newProperty = document.createElement('div');
                    newProperty.className = 'property-card';
                    newProperty.innerHTML = `
                        <div class="property-image" style="background-image: url('https://via.placeholder.com/400x300');"></div>
                        <div class="property-details">
                            <h3>Nueva propiedad ${i+1}</h3>
                            <p class="location"><i class="fas fa-map-marker-alt"></i> Ubicación ejemplo</p>
                            <div class="property-features">
                                <span><i class="fas fa-bed"></i> 3 hab.</span>
                                <span><i class="fas fa-bath"></i> 2 baños</span>
                                <span><i class="fas fa-ruler-combined"></i> 120 m²</span>
                            </div>
                            <div class="property-footer">
                                <p class="price">$15,000 MXN/mes</p>
                                <a href="#" class="btn">Ver detalles</a>
                            </div>
                        </div>
                    `;
                    propertyGrid.appendChild(newProperty);
                }
                this.textContent = 'Cargar más propiedades';
            }, 1000);
        });
    }
