// Manejar el menú móvil
document.addEventListener('DOMContentLoaded', function() {
    // Toggle del menú móvil (si se añade)
      const toggle = document.getElementById('menu-toggle');
  const nav = document.getElementById('nav-links');

  toggle.addEventListener('click', () => {
    nav.classList.toggle('active');
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
    const togglePassword = document.querySelector('.toggle-password');
    if (togglePassword) {
        togglePassword.addEventListener('click', function() {
            const passwordInput = this.previousElementSibling;
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
            this.classList.toggle('fa-eye');
            this.classList.toggle('fa-eye-slash');
        });
    }
    
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
});