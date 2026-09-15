<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Página con zoom al 110%</title>
  <style>
    /* Escala general de la página incrementada un 10% */
    html {
      zoom: 1.1; /* Método directo para ampliar toda la interfaz */
    }

    /* Alternativa mediante transform si buscas compatibilidad específica */
    /*
    body {
      transform: scale(1.1);
      transform-origin: top center;
      width: 90.9%; /* Compensación para evitar scroll horizontal */
    }
    */

    /* Estilos del Switch en su tamaño estándar original */
    .switch {
      position: relative;
      display: inline-block;
      width: 50px;
      height: 26px;
    }

    .switch input {
      opacity: 0;
      width: 0;
      height: 0;
    }

    .slider {
      position: absolute;
      cursor: pointer;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: #ccc;
      transition: 0.3s;
      border-radius: 26px;
    }

    .slider:before {
      position: absolute;
      content: "";
      height: 20px;
      width: 20px;
      left: 3px;
      bottom: 3px;
      background-color: white;
      transition: 0.3s;
      border-radius: 50%;
    }

    input:checked + .slider {
      background-color: #2563eb;
    }

    input:checked + .slider:before {
      transform: translateX(24px);
    }
  </style>
</head>
<body>

  <!-- Switch restaurado a sus proporciones base -->
  <label class="switch">
    <input type="checkbox">
    <span class="slider"></span>
  </label>

</body>
</html>
