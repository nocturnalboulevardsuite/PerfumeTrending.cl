/* Estilo base para todos los botones de la interfaz */
.btn-zoom,
button,
.nav-button {
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), 
              box-shadow 0.2s ease, 
              background-color 0.2s ease;
  will-change: transform;
}

/* Efecto Hover Minimalista */
.btn-zoom:hover,
button:hover,
.nav-button:hover {
  transform: scale(1.035);
  cursor: pointer;
}

/* Respuesta táctil/click */
.btn-zoom:active,
button:active,
.nav-button:active {
  transform: scale(0.98);
}
