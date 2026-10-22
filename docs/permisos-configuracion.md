# Permisos y configuración

D1, 2026-10-22. Referencia del comportamiento implementado; el orden de trabajo sigue en [plan-desarrollo.md](plan-desarrollo.md).

## Matriz de acceso

| Capacidad | Técnico activo, staff y superusuario | Administrador de empresa activo | Trabajador activo |
| --- | --- | --- | --- |
| Django Admin, `/administracion/` | Sí, ámbito global | No | No |
| Mantenimiento, GET/POST `/configuracion/` | Sí, afecta a todas las empresas | No, 403 | No, 403 fuera de mantenimiento |
| Nombre y tolerancia, GET/POST `/configuracion/empresa/` | Solo si además tiene perfil administrador y empresa activos | Solo su empresa | No, 403 fuera de mantenimiento |
| Operación cliente | Según su perfil; el privilegio técnico no concede una empresa | Su empresa | Sus operaciones autorizadas |
| Acceso durante mantenimiento | Sí | Sí, su empresa; no puede desactivarlo | Pantalla informativa, 503 |

- Un usuario staff sin superusuario, o superusuario sin staff, no administra la plataforma. Tener permisos individuales de modelos no cambia esta regla.
- Una cuenta `User.is_active=False` no conserva acceso autenticado con el backend de Django configurado; las rutas protegidas redirigen al inicio de sesión.
- Un perfil inactivo, sin empresa o con empresa inactiva recibe 403 en las rutas cliente, tanto GET como POST. Puede cerrar sesión. La empresa es obligatoria en la base actual; el caso sin empresa se mantiene cerrado también en el permiso compartido.
- Un técnico con perfil inactivo conserva acceso a mantenimiento y Django Admin para recuperación, pero no a las rutas operativas de ese perfil.
- Un usuario sin perfil no puede editar configuración de empresa; conserva las respuestas sin datos/no asignado o denegadas de las rutas existentes. No se le asigna una empresa automáticamente.
- El mantenimiento global bloquea trabajadores, no todas las escrituras. Los administradores de empresa siguen operando. Para una migración que requiera detener toda escritura, parar los procesos de aplicación; activar este modo por sí solo no es suficiente.

## Inventario de rutas y fronteras

| Rutas | Frontera de autorización |
| --- | --- |
| `/administracion/…` | `TechnicalAdminSite`, condición técnica compartida con mantenimiento |
| `/configuracion/` | `is_technical_admin`, comprobado antes de obtener o guardar configuración |
| `/configuracion/empresa/` | `require_company_admin`; la instancia se obtiene del perfil autenticado |
| `/empleados/…` | Administrador de empresa para gestión de empleados |
| `/turnos/…` | Lectura por rol/empresa; creación, copia, edición, duplicado y cancelación para administrador |
| `/fichar/`, `/fichajes/…`, `/mis-horas/` | Fichaje y lectura según perfil; manual/corrección para administrador de empresa |
| `/solicitudes/…`, `/incidencias/…` | Propias para trabajador, gestión de la empresa para administrador; revisión/resolución protegida |
| `/informes/mensual/`, `/informes/mensual/csv/` | Resúmenes y exportación acotados a la empresa autorizada |
| `/` | Panel según perfil; técnico sin perfil no obtiene un panel operativo global |
| `/iniciar-sesion/`, `/cerrar-sesion/`, `/static/…` | Exentos del bloqueo de mantenimiento y perfil; autenticación/CSRF conservan sus controles |

La barrera de perfiles/empresas inactivos se aplica en `MaintenanceModeMiddleware` antes de ejecutar las vistas. Los permisos de rol y el filtrado de entidades continúan en las vistas/selectores. Ocultar enlaces es una ayuda visual; la autorización se exige en servidor.

## Propiedad de la configuración

| Dato | Fuente vigente | Edición |
| --- | --- | --- |
| Nombre de la empresa | `Company.name` | Administrador de esa empresa o técnico desde Admin |
| Margen para detectar entrada ausente en panel de administrador | `Company.clock_tolerance_minutes` | Administrador de esa empresa o técnico desde Admin |
| IP permitida y credencial QR | `Workplace.public_wifi_ip`, `qr_token_hash` | Técnico desde centros de trabajo; seguridad de red pendiente de D2 |
| Activación, ventana, motivo y mensaje de mantenimiento | `BusinessConfig` singleton | Técnico |
| Zona horaria efectiva de la aplicación | `config.settings.TIME_ZONE` | Configuración de despliegue; sin zonas por empresa todavía |
| Otros datos de empresa/centro | `Company`, `Workplace` | Técnico desde Admin; recorrido autónomo pendiente de D7 |

Los antiguos campos de nombre, tolerancia, QR/IP y zona horaria de `BusinessConfig` permanecen para compatibilidad histórica. No son la fuente operativa de nombre/tolerancia/QR/IP ni sustituyen `TIME_ZONE`. La nueva pantalla global solo permite mantenimiento. La marca visual Xarlot sigue siendo fija; el nombre editable es el de la empresa.

## Migración y evidencia

- `companies.0004` crea la tolerancia por empresa, con valor inicial 5. Cuando existe configuración global, copia su tolerancia a todas las empresas existentes, también inactivas: todas utilizaban antes ese mismo valor. Conserva los nombres y no crea configuración global si no existía.
- Las empresas nuevas parten de 5 minutos. El formulario rechaza valores negativos, no numéricos y superiores a 32767, límite portable del campo utilizado.
- `core.test_configuration_access`: reproducción del fallo original, matriz GET/POST, intentos de enviar otra empresa y campos globales, ausencia de cambios ajenos, mantenimiento técnico, navegación, bajas y tolerancias diferentes con dos empresas.
- `companies.test_migrations`: ensayo con esquemas históricos, valor global personalizado y caso sin configuración.
- `core.tests`, `core.test_admin_access` y la regresión completa conservan la cobertura previa.

Los resultados ejecutados y la copia local se registran en [estado-sesion.md](estado-sesion.md). D1 no acredita despliegue, capacidad ni concurrencia en PostgreSQL; esas verificaciones siguen en D4–D8.
