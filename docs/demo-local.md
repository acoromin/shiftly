# Demo local de Café Brisa

Esta demo es ficticia y sirve para recorrer las pantallas desde dos roles. Solo se crea en SQLite con `DEBUG=True`; el comando rechaza una base con perfiles reales. No modifica la cuenta técnica existente.

## Abrirla

```bash
cd /home/acoromin/Documents/shiftly
./.venv/bin/python manage.py runserver
```

Abrir <http://127.0.0.1:8000/>. Entrar como `demo_admin` para gestionar la cafetería o como `demo_ana`/`demo_luis` para ver el recorrido del trabajador. La contraseña y el enlace del QR local están en `backups/demo-access.txt` (archivo local ignorado por Git, permisos `0600`). `acoromin` conserva su acceso técnico en `/administracion/`.

El comando `./.venv/bin/python manage.py seed_local_demo` crea la demo en una base local vacía y, si ya existe, informa de la ruta de credenciales sin duplicar datos. La empresa Xarlot sembrada por la aplicación permanece separada y sin perfiles demo. Café Brisa tiene una jefa, dos trabajadores, un centro, turnos próximos e históricos, fichajes, una solicitud pendiente, otra aprobada y una incidencia pendiente.

El QR de prueba se configura para `127.0.0.1`; permite recorrer el fichaje desde el navegador de **este ordenador**. Desde un móvil físico de la red local se detectará otra IP y se bloqueará, como exige el control de IP. Para un móvil real hace falta configurar la IP que ve el servidor y un entorno de acceso apropiado; la validación de staging sigue pendiente en D2.

## Revisión móvil realizada

Inspección con Chrome a **390 × 844 px**: acceso, panel y turnos de administrador, lista de empleados, panel y turnos de trabajador, fichaje sin QR y con QR. El menú móvil se abre; no se observó desbordamiento horizontal de la página en esas pantallas. El QR activa el botón de entrada y el navegador retira el fragmento de la barra.

Hallazgos para la etapa de experiencia de cliente:

- La tabla de empleados usa desplazamiento horizontal en móvil; es funcional, pero dificulta comparar datos y acciones de una persona.
- La semana empieza por el lunes aunque el usuario entre al final de la semana. En domingo se recorren varias tarjetas de días pasados antes de ver el turno actual; conviene ofrecer un salto al día de hoy o un resumen inicial.
- Las métricas del panel se apilan en una columna. Se leen bien, pero las acciones secundarias quedan bastante abajo.

Las capturas locales están en `backups/demo-previews/` y no se suben a Git. Esta revisión visual no sustituye pruebas con un móvil físico ni la comprobación del proxy/QR impreso exigida para cerrar D2.
