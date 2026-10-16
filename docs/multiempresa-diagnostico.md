# Diagnostico multiempresa

Este documento forma parte de la Fase 1 del plan de refactorizacion. No define modelos nuevos ni cambia comportamiento. Su objetivo es dejar inventariadas las zonas que hoy operan como aplicacion de una sola empresa y que deben filtrarse por empresa en fases posteriores.

## Alcance de esta fase

- Mantener el comportamiento actual como base de regresion.
- Identificar consultas globales peligrosas.
- Identificar formularios que muestran datos sin filtrar por empresa.
- Identificar servicios y vistas con logica de negocio no preparada para multiempresa.
- No crear `companies` todavia.
- No crear migraciones todavia.
- No cambiar interfaz todavia.

## Resumen de riesgo

El proyecto usa una unica base de datos y actualmente no existe un campo `empresa` en los modelos operativos. En una arquitectura multiempresa, cualquier consulta global de empleados, turnos, fichajes, solicitudes, incidencias o informes podria exponer datos de otra empresa si se mantiene sin filtrar.

La regla futura debe ser: ninguna vista de cliente debe consultar todos los registros de un modelo operativo. Las vistas deben consultar datos de la empresa actual mediante selectors, servicios y permisos explicitos.

## Configuracion global actual

`core.models.BusinessConfig` funciona como singleton mediante `get_solo()` y almacena configuracion de negocio global:

- nombre del negocio,
- IP publica permitida,
- token QR protegido,
- tolerancia de fichaje,
- modo mantenimiento.

En multiempresa, esta responsabilidad debe separarse:

- configuracion de empresa,
- configuracion de centro de trabajo,
- configuracion global tecnica de plataforma si fuese necesaria.

El QR y la IP deben pasar a pertenecer al centro de trabajo, no a una configuracion global unica.

## Queries globales por app

### `employees`

Archivo: `employees/views.py`

- `EmployeeProfile.objects.select_related('user').order_by(...)` lista todos los empleados.
- `EmployeeProfile.objects.filter(is_active=True).count()` cuenta todos los empleados activos.
- `get_object_or_404(EmployeeProfile.objects.select_related('user'), pk=pk)` permite localizar empleados por `pk` sin empresa.

Archivo: `employees/forms.py`

- La validacion de `username` usa `User.objects.filter(username__iexact=...)`. Esto puede seguir siendo global si el login es unico en plataforma, pero debe decidirse explicitamente.

Riesgo futuro: un administrador de una empresa podria listar, editar, activar/desactivar o cambiar la contrasena de empleados de otra empresa si solo se valida el rol.

### `scheduling`

Archivo: `scheduling/views.py`

- La vista semanal consulta turnos activos por rango de fechas sin empresa.
- La vista mensual consulta turnos activos por rango de fechas sin empresa.
- Edicion, duplicado y cancelacion usan `get_object_or_404(Shift, pk=pk, is_active=True)` sin empresa.
- `copy_previous_week` copia turnos de la semana anterior consultando todos los turnos activos del rango.

Archivo: `scheduling/forms.py`

- `self.fields['employee'].queryset = EmployeeProfile.objects.filter(is_active=True)` muestra todos los empleados activos.

Archivo: `scheduling/models.py`

- `Shift.clean()` valida solapes consultando `Shift.objects.filter(employee=..., ...)` sin empresa ni centro.

Riesgo futuro: un administrador podria crear turnos con empleados de otra empresa o editar/cancelar turnos ajenos mediante URL directa.

### `timeclock`

Archivo: `timeclock/views.py`

- El historico para administradores usa todos los fichajes.
- La correccion usa `get_object_or_404(TimeClockEntry.objects.select_related('employee'), pk=pk)` sin empresa.
- El fichaje manual usa un formulario con todos los empleados activos.

Archivo: `timeclock/forms.py`

- `ManualTimeClockEntryForm` muestra todos los empleados activos.

Archivo: `timeclock/services.py`

- `attempt_clock()` usa `BusinessConfig.get_solo()` para validar un QR y una IP globales.
- `employees_with_open_clock_entries()` usa todos los empleados activos si no recibe queryset.
- `create_audit_log()` no guarda empresa.

Riesgo futuro: los fichajes podrian validarse contra la IP/QR de otro centro o mostrarse entre empresas.

### `leaves`

Archivo: `leaves/views.py`

- El administrador ve todas las solicitudes.
- La revision usa `get_object_or_404(LeaveRequest, pk=pk)` sin empresa.
- El trabajador cancela con `employee=profile`, lo cual protege datos propios pero no resuelve el caso admin multiempresa.

Archivo: `leaves/models.py`

- La validacion de solapes consulta solicitudes del empleado sin empresa.

Riesgo futuro: un administrador podria revisar solicitudes de otra empresa si conoce el identificador.

### `incidents`

Archivo: `incidents/views.py`

- El administrador ve todas las incidencias.
- La resolucion usa `get_object_or_404(Incident, pk=pk)` sin empresa.

Riesgo futuro: un administrador podria ver o resolver incidencias de otra empresa.

### `dashboard`

Archivo: `dashboard/views.py`

- Cuenta todos los empleados activos.
- Cuenta todas las solicitudes pendientes.
- Cuenta todas las incidencias pendientes.
- Muestra turnos de hoy sin empresa.
- Muestra fichajes recientes sin empresa.
- Muestra fichajes bloqueados sin empresa.
- Busca ausencias aprobadas sin empresa.
- Busca fichajes de hoy sin empresa.
- Crea incidencias automaticas desde turnos globales.

Riesgo futuro: el panel principal es una de las mayores superficies de fuga de datos porque agrega informacion de varias apps y ademas puede crear incidencias.

### `payroll`

Archivo: `payroll/services.py`

- `recalculate_month()` recorre todos los empleados activos.
- `generate_payroll_draft()` genera un borrador con todos los empleados activos.
- `calculate_employee_summary()` consulta turnos, fichajes, solicitudes e incidencias sin empresa.

Riesgo futuro: los informes mensuales y CSV podrian mezclar empleados de varias empresas.

### `reports`

Archivo: `reports/views.py`

- `monthly_summary()` recalcula el mes completo sin empresa.
- `payroll_csv()` genera CSV global.
- La generacion de CSV crea un borrador en una peticion GET.

Riesgo futuro: exportacion de datos laborales de otras empresas.

### `core`

Archivo: `core/views.py`

- La configuracion usa siempre `BusinessConfig.get_solo()`.
- La auditoria de mantenimiento no incluye empresa.

Archivo: `core/middleware.py`

- El modo mantenimiento es global.

Archivo: `core/context_processors.py`

- El estado de mantenimiento es global.

Riesgo futuro: activar mantenimiento para una empresa podria bloquear a todos los clientes si no se separa configuracion de empresa/plataforma.

## Acoplamientos de producto actuales

- El README describe una aplicacion del bar.
- Los textos de fichaje mencionan el WiFi y QR del bar.
- El mantenimiento se explica como tarea de lunes por cierre del bar.
- Los puestos estan limitados a `camarero` y `cocinero`.
- El nombre visible y tecnico `Xarlot` aparece en templates, admin, README y CSV.
- La seccion de informes usa el concepto de pre-nomina; debe tratarse con cuidado para no prometer nomina legal definitiva.

## Refactor futuro recomendado

La migracion multiempresa debe avanzar en pasos pequenos:

1. Crear modelos base en `companies`: `Company`, `Workplace`, `JobPosition`.
2. Crear una empresa inicial para los datos actuales.
3. Migrar IP/QR global al primer centro de trabajo.
4. Migrar `camarero` y `cocinero` a puestos configurables.
5. Anadir `empresa` y `centro` a los modelos operativos de forma gradual.
6. Crear selectors para consultas filtradas.
7. Adaptar formularios para recibir empresa actual.
8. Adaptar permisos para impedir acceso cruzado por URL.
9. Reorientar informes por empresa y periodo.
10. Generalizar interfaz despues de asegurar aislamiento de datos.

## Tests de aislamiento que se deben anadir en fases posteriores

- Un administrador de Empresa A no lista empleados de Empresa B.
- Un administrador de Empresa A no edita empleados de Empresa B por URL directa.
- Un trabajador solo ve sus turnos, fichajes, solicitudes, horas e incidencias.
- Los formularios de turnos solo muestran empleados, centros y puestos de la empresa actual.
- Los formularios de fichaje manual solo muestran empleados de la empresa actual.
- Un QR de un centro no sirve para otro centro.
- Una IP de un centro no sirve para otro centro.
- Los informes mensuales solo incluyen empleados de la empresa actual.
- Los CSV no mezclan empresas.
- Los audit logs registran empresa.

## Criterio de salida de Fase 1

La Fase 1 termina cuando:

- este diagnostico esta versionado,
- los tests de regresion actuales pasan,
- los nuevos tests no requieren modelos nuevos,
- no se han creado migraciones,
- no se ha cambiado comportamiento funcional.
