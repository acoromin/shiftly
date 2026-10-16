# Xarlot

Aplicación web para gestionar empleados, turnos, fichajes, solicitudes, incidencias y resúmenes mensuales del bar.

## Arranque local

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py runserver
```

La aplicación estará disponible en `http://127.0.0.1:8000/`.

## Ventana de mantenimiento

El bar cierra los lunes. Por ese motivo, el lunes es el día recomendado para actualizaciones, migraciones, comprobaciones y copias de seguridad.

El mantenimiento **no se activa automáticamente los lunes**. Un administrador debe activarlo o programarlo desde:

`Configuración > Modo mantenimiento`

También puede activarse cualquier otro día si existe una emergencia grave.

Durante el modo mantenimiento:

- Los trabajadores ven una pantalla informativa.
- Los trabajadores no pueden fichar.
- Los trabajadores no pueden crear solicitudes ni incidencias.
- Los trabajadores no pueden consultar sus pantallas.
- Los administradores mantienen el acceso completo.

## Proceso recomendado para los lunes

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
