# Xarlot

Aplicación web para gestionar empleados, turnos, fichajes, solicitudes, incidencias y resúmenes mensuales del bar.

## Desarrollo y estado

El [plan de desarrollo vigente](docs/plan-desarrollo.md) define las etapas para preparar el producto multiempresa, su operación y un piloto real. La [bitácora de continuidad](docs/estado-sesion.md) indica qué está verificado y la siguiente tarea. La configuración incluida actualmente corresponde al entorno de desarrollo.

## Arranque local

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py runserver
```

La aplicación estará disponible en `http://127.0.0.1:8000/`.

## Acceso al administrador técnico

`/administracion/` está reservado a superusuarios técnicos activos con `is_staff=True`.
El permiso `is_staff` y los permisos individuales de modelos no bastan para acceder.
Los administradores de empresa gestionan empleados, turnos, fichajes e informes desde las pantallas normales, limitadas a su empresa.

En **Configuración de empresa** (`/configuracion/empresa/`) pueden cambiar el nombre y la tolerancia para detectar entradas ausentes en el panel de su empresa. La migración `companies.0004` conserva la tolerancia global anterior en las empresas existentes; las nuevas parten de 5 minutos. Consulta la [matriz de permisos y configuración](docs/permisos-configuracion.md).

Para crear una cuenta técnica en un entorno local nuevo:

```bash
./.venv/bin/python manage.py createsuperuser
```

## Centros y fichaje por QR

Cada empleado puede tener un centro principal y cada turno puede indicar su centro. Al duplicar o copiar un turno se conserva el centro del turno original. El fichaje usa el centro del turno activo; si no hay turno activo con centro, el QR identifica un centro activo de la empresa del empleado. La IP pública debe coincidir con la configurada en ese centro.

El superusuario técnico puede configurar la IP en `/administracion/companies/workplace/` y generar un QR desde la acción **Generar QR para los centros seleccionados**. La URL resultante se muestra una sola vez y debe guardarse para imprimir el QR. La acción **Revocar QR** invalida el anterior. También puede configurarse desde consola:

```bash
./.venv/bin/python manage.py setup_xarlot_clock --workplace-id ID --wifi-ip IP_PUBLICA --base-url https://tu-dominio
```

Los campos QR/IP antiguos de `BusinessConfig` ya no autorizan fichajes. La migración `companies.0003` copia sus valores a un centro cuando existe uno solo; con varios centros, configura cada uno explícitamente antes de usar sus QR.

El QR nuevo usa un identificador público de centro y un secreto en el fragmento de la URL; el secreto se envía al fichar por POST. Los QR antiguos con `?token=` siguen admitidos durante la transición y se pueden desactivar con `CLOCK_ALLOW_LEGACY_QR=0` después de reimprimirlos. La IP se toma de la conexión salvo que se declare un proxy confiable en `TRUSTED_PROXY_CIDRS`. La [guía de seguridad y transición del fichaje](docs/seguridad-fichaje-d2.md) explica configuración, impresión, rotación, límites de intentos y verificaciones de staging pendientes.

## Ventana de mantenimiento

El mantenimiento afecta a todas las empresas. Acuerda la ventana con sus responsables; el día de cierre de un local no determina el de los demás.

Solo un técnico activo, staff y superusuario puede activarlo o programarlo desde:

`Mantenimiento global` (`/configuracion/`)

También puede activarse cualquier otro día si existe una emergencia grave.

Durante el modo mantenimiento:

- Los trabajadores ven una pantalla informativa.
- Los trabajadores no pueden fichar.
- Los trabajadores no pueden crear solicitudes ni incidencias.
- Los trabajadores no pueden consultar sus pantallas.
- Los administradores de empresa mantienen acceso a su empresa, pero no pueden gestionar el mantenimiento.

Este modo no detiene todas las escrituras: los administradores siguen operando. Cuando una copia o migración requiera detenerlas, deben pararse los procesos de aplicación.

## Proceso de mantenimiento técnico

1. Hacer una copia de seguridad de la base de datos.
2. Activar el modo mantenimiento desde Xarlot.
3. Aplicar los cambios de código.
4. Ejecutar las migraciones.
5. Comprobar que la aplicación arranca correctamente.
6. Comprobar el inicio de sesión del administrador.
7. Comprobar los fichajes.
8. Comprobar los turnos.
9. Comprobar las solicitudes.
10. Comprobar la exportación CSV para gestoría.
11. Revisar los registros de error.
12. Desactivar el modo mantenimiento.

### Copia de seguridad con SQLite

Crear la carpeta de copias si todavía no existe:

```bash
mkdir -p backups
```

Crear una copia con fecha y hora:

```bash
cp db.sqlite3 "backups/xarlot-$(date +%Y%m%d-%H%M%S).sqlite3"
```

Comprobar que se ha creado:

```bash
ls -lh backups/
```

### Aplicar cambios y migraciones

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py check
python manage.py test
```

Después, iniciar la aplicación y realizar las comprobaciones funcionales antes de desactivar el mantenimiento.

## Mantenimiento de emergencia

Si ocurre un fallo grave fuera del lunes:

1. Activar inmediatamente el modo mantenimiento.
2. Indicar el motivo y, si se conoce, la hora prevista de finalización.
3. Hacer una copia de seguridad antes de modificar datos.
4. Aplicar y comprobar la corrección.
5. Desactivar el mantenimiento cuando la aplicación vuelva a ser estable.
