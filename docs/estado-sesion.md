# Estado de sesion

Fecha ultima actualizacion: 2026-09-07

Este archivo es la fuente operativa principal del proyecto. Si el usuario dice `mira estado-sesion`, leer este archivo primero, comprobar el estado real del repo y actuar segun `Siguiente Accion Operativa`.

## Reglas Para Retomar

- Usar siempre `./.venv/bin/python`; `python` global no existe y `python3` global no tiene Django.
- Antes de editar, ejecutar o revisar `git status --short` y no revertir cambios no propios.
- No ejecutar fases posteriores anticipadamente.
- Mantener cada fase pequena, verificable y funcional al terminar.
- Flujo obligatorio por fase: audit -> protect write paths -> migrate/backfill if needed -> enforce invariant -> tests -> full regression -> documentation.
- Antes de imponer `NOT NULL`, constraint o cambio de dominio, demostrar con consultas que los datos actuales no bloquean.
- No tocar `workplace`, `BusinessConfig`, QR/IP por centro, templates ni diseno visual salvo que la fase activa lo diga explicitamente.
- No borrar ni reescribir el historico de lo hecho; este archivo debe funcionar como bitacora acumulativa.
- Si hay que mejorar contexto, anadir una seccion nueva o actualizar solo las secciones operativas de estado/siguiente accion.
- Al cerrar cada sesion, actualizar este archivo con lo hecho, lo verificado, lo pendiente y el siguiente paso recomendado.

## Siguiente Accion Operativa

- Primero estabilizar la fase recien hecha si sigue sin commit o sin migracion aplicada en la base usada.
- Comprobar `git status --short`.
- Comprobar `./.venv/bin/python manage.py showmigrations incidents`.
- Si `incidents.0007_alter_incident_company` no esta aplicada en la base local y se va a continuar sobre esa base, ejecutar `./.venv/bin/python manage.py migrate incidents` o `./.venv/bin/python manage.py migrate` antes de nuevas auditorias de datos.
- Siguiente fase tecnica: `fase-hardening-timeclockentry-company-not-null`.
- Motivo: payroll depende de fichajes y no debe endurecerse antes de que `TimeClockEntry.company` sea fiable.
- No adelantar payroll ni workplace antes de cerrar `TimeClockEntry.company`.

## Estado Actual Del Proyecto

- Fase actual implementada en codigo: `fase-hardening-incident-company-not-null`.
- Ultimo commit conocido antes de esa fase: `feb6fc4` (`fase-hardening-leaverequest-company-not-null`).
- La fase de incident esta en el worktree; si no se ha hecho commit, tratarla como cambios pendientes propios y no revertirla.
- `EmployeeProfile.company` es obligatorio.
- `Shift.company` es obligatorio.
- `LeaveRequest.company` es obligatorio.
- `Incident.company` es obligatorio en codigo y migracion `incidents/migrations/0007_alter_incident_company.py`.
- `TimeClockEntry.company` sigue nullable y es el siguiente hueco critico.
- `MonthlyHoursSummary.company`, `PayrollDraft.company` y `PayrollDraftLine.company` siguen nullable.
- `EmployeeProfile.primary_workplace`, `Shift.workplace` y `TimeClockEntry.workplace` siguen nullable y fuera del siguiente paso.
- Admin operativo sin `company` esta cerrado en vistas cliente.
- Staff/superuser sin perfil no tiene panel operativo global de cliente.
- Django Admin tecnico aun no esta aislado por tenant.
- `BusinessConfig` sigue siendo global para QR/IP/mantenimiento.
- `docs/multiempresa-diagnostico.md` es historico/obsoleto y no debe usarse como estado actual.
- `docs/hardening-company-not-null-plan.md` es plan historico de la primera etapa; la fuente viva es este archivo.

## Ultima Auditoria De Datos

Fecha: 2026-09-07

- `Company`: 1.
- `Workplace`: 1.
- `JobPosition`: 2.
- `BusinessConfig`: 1.
- `EmployeeProfile`: total 1, `company=NULL` 0, `primary_workplace=NULL` 0, mismatch workplace/company 0.
- `Shift`: total 0, `company=NULL` 0, `workplace=NULL` 0, mismatches 0.
- `TimeClockEntry`: total 2, `company=NULL` 0, `workplace=NULL` 0, mismatches employee/company 0, workplace/company 0, related_shift/company 0, related_shift/employee 0.
- `LeaveRequest`: total 0, `company=NULL` 0, mismatch employee/company 0.
- `Incident`: total 0, `company=NULL` 0, mismatches 0.
- `MonthlyHoursSummary`: total 1, `company=NULL` 0, mismatch employee/company 0.
- `PayrollDraft`: total 1, `company=NULL` 0, drafts con lineas mixtas 0, drafts vacios 0.
- `PayrollDraftLine`: total 1, `company=NULL` 0, mismatch employee/company 0, mismatch draft/company 0.
- Nota: en esa auditoria local, `incidents.0007_alter_incident_company` no constaba como aplicada en `django_migrations`.

## Ultimas Validaciones Ejecutadas

Fase `fase-hardening-incident-company-not-null`:

- Auditoria previa: `Incident` total 0, `company=NULL` 0 e inconsistencias 0.
- `./.venv/bin/python manage.py test incidents timeclock dashboard payroll`: 66 tests OK.
- `./.venv/bin/python manage.py test`: 149 tests OK.
- `./.venv/bin/python manage.py check`: OK.
- `./.venv/bin/python manage.py makemigrations --check --dry-run`: sin cambios pendientes.
- `git diff --check`: OK.

Validaciones historicas relevantes:

- Verificacion previa de fase amplia: `./.venv/bin/python manage.py test employees scheduling timeclock leaves incidents dashboard reports core` paso: 140 tests OK.
- Verificacion previa de suite completa: `./.venv/bin/python manage.py test` paso: 155 tests OK.
- Verificacion previa de sistema: `./.venv/bin/python manage.py check` paso sin errores.
- Verificacion previa de migraciones: `./.venv/bin/python manage.py makemigrations --check --dry-run` no detecto cambios pendientes.
- Verificacion previa de espacios: `git diff --check` paso sin errores.
- `fase-hardening-company-not-null-plan`: `check` OK, `makemigrations --check --dry-run` OK, `git diff --check` OK y `git status --short` quedo limpio antes de editar documentacion.
- `fase-hardening-employeeprofile-company-not-null`: `./.venv/bin/python manage.py test employees` 19 OK, suite global 149 OK, `check` OK, `makemigrations --check --dry-run` OK, `git diff --check` OK.
- `fase-hardening-shift-company-not-null`: `./.venv/bin/python manage.py test scheduling` 29 OK, suite global 149 OK, `check` OK, `makemigrations --check --dry-run` OK, `git diff --check` OK.
- `fase-hardening-leaverequest-company-not-null`: `./.venv/bin/python manage.py test leaves` 18 OK, suite global 149 OK, `check` OK, `makemigrations --check --dry-run` OK, `git diff --check` OK.

## Historial Detallado Conservado

- Cerrada la fase `fase-auditoria-company-null` en commit `3d3fa12`.
- Implementada la fase `fase-cierre-admin-sin-company`.
- Creado helper compartido `employees.permissions` para distinguir admin operativo con empresa de admin sin empresa.
- No se ha hecho backfill desde la fase documental posterior a la auditoria, porque los datos auditados no lo requerian.
- Se han creado migraciones unicas de esquema para `EmployeeProfile.company`, `Shift.company`, `LeaveRequest.company` e `Incident.company`.
- No se ha cambiado el diseno visual.
- No se han tocado templates.
- No se han hecho obligatorios `primary_workplace`, `workplace` ni `company` en otros modelos distintos de los ya cerrados.
- `EmployeeForm` cliente sigue sin exponer `company`; `employee_create()` asigna empresa desde el admin actual.
- `Shift.workplace` sigue nullable y fuera de alcance.
- Las rutas de crear, editar, duplicar y copiar turnos aplican contexto de empresa existente.
- Las rutas de creacion, listado, cancelacion y revision de solicitudes mantienen proteccion por empresa existente.
- Las rutas de creacion manual, deteccion de entrada ausente y deteccion de salida ausente de incidencias mantienen asignacion de empresa existente.
- No se ha habilitado panel operativo global para staff/superuser.
- Django Admin solo se ha ajustado para exponer `EmployeeProfile.company`, `Shift.company`, `LeaveRequest.company` e `Incident.company`.
- No se ha modificado `core.settings`, que queda como configuracion interna/global existente.
- No se ha tocado QR/IP por centro.
- No se ha aplicado hardening masivo.
- No se ha tocado payroll/reports salvo fixtures de tests que creaban solicitudes o incidencias sin empresa.
- No se ha cambiado la semantica de formularios ni listados de trabajadores.

## Vistas Operativas Cerradas Para Admin Sin Empresa

- `dashboard.views.index()` devuelve 403 para admin sin empresa.
- `employees.views` exige admin con empresa para listar, crear, editar, activar/desactivar y cambiar contrasenas.
- `scheduling.views` exige admin con empresa para gestionar turnos y bloquea semana/mes para admin sin empresa.
- `timeclock.views` exige admin con empresa para historial de equipo, fichaje manual y correccion de fichajes.
- `leaves.views` exige admin con empresa para listado administrativo y revision de solicitudes.
- `incidents.views` exige admin con empresa para listado administrativo y resolucion de incidencias.
- `reports.views` exige admin con empresa para resumen mensual y CSV de pre-nomina.

## Tests Actualizados Historicos

- Tests que antes verificaban modo global temporal de admin sin empresa ahora esperan 403.
- Tests genericos de admin operativo se han ajustado para crear admin con empresa.
- Tests de admin con empresa siguen verificando aislamiento por empresa.
- Tests de trabajadores se mantienen para comprobar comportamiento propio.
- Eliminados o reconducidos tests que trataban `EmployeeProfile.company=NULL` como estado normal.
- Tests que aun necesitan permisos negativos usan usuario sin perfil cuando el estado `admin sin company` ya no es representable por base de datos.
- Tests de otras apps se han ajustado para crear siempre `EmployeeProfile` con empresa.
- Eliminados o reconducidos tests que trataban `Shift.company=NULL` como estado normal.
- Tests de otras apps se han ajustado para crear siempre `Shift` con empresa.
- Eliminados o reconducidos tests que trataban `LeaveRequest.company=NULL` como estado normal.
- Tests de otras apps se han ajustado para crear siempre `LeaveRequest` con empresa.
- Eliminados o reconducidos tests que trataban `Incident.company=NULL` como estado normal.
- Tests de otras apps se han ajustado para crear siempre `Incident` con empresa.

## Invariantes Cerradas

- Admin con `company` mantiene gestion operativa limitada a su empresa.
- Admin sin `company` ya no puede usar paneles operativos de cliente.
- Trabajadores mantienen comportamiento propio.
- Selectors por empresa fallan cerrado con `company=None` en empleados, turnos, fichajes, solicitudes, incidencias y summaries.
- `EmployeeProfile.company` no permite `null=True` ni `blank=True`.
- `Shift.company` no permite `null=True` ni `blank=True`.
- `LeaveRequest.company` no permite `null=True` ni `blank=True`.
- `Incident.company` no permite `null=True` ni `blank=True`.
- Django Admin expone `company` en `EmployeeProfile`, `Shift`, `LeaveRequest` e `Incident` para no romper creacion tecnica.

## Invariantes Pendientes

- `TimeClockEntry.company` debe ser obligatorio.
- `MonthlyHoursSummary.company` debe ser obligatorio.
- `PayrollDraft.company` debe ser obligatorio salvo decision explicita de borradores globales.
- `PayrollDraftLine.company` debe ser obligatorio y coincidir con `draft.company` y `employee.company`.
- `TimeClockEntry.related_shift.employee` debe coincidir con `TimeClockEntry.employee`.
- `Incident.shift.employee` debe coincidir con `Incident.employee`.
- `Incident.timeclock_entry.employee` debe coincidir con `Incident.employee`.
- `LeaveRequest.reviewed_by` e `Incident.resolved_by` deberian validarse contra la misma empresa cuando exista perfil.
- `EmployeeProfile.company` es mutable y podria mover historico; falta decidir si bloquear cambios o modelar historial.
- `workplace` todavia no es una invariante fuerte.
- QR/IP por fichaje siguen en `BusinessConfig` global y deben moverse a `Workplace` en una fase posterior.
- Django Admin no esta filtrado por tenant.
- `AuditLog` no guarda `company` ni `workplace`.
- `reports` y `dashboard` conservan side effects en GET.

## Fases Cerradas

- `fase-seed-empresa-inicial`: modelos base de empresa/centro/puestos y seed inicial.
- `fase-employeeprofile-empresa-centro`: `EmployeeProfile.company` y `EmployeeProfile.primary_workplace` con backfill.
- `fase-shift-empresa-centro`: `Shift.company` y `Shift.workplace` con backfill.
- `fase-timeclock-empresa-centro`: `TimeClockEntry.company` y `TimeClockEntry.workplace` con backfill.
- `fase-timeclock-service-contexto-empresa-centro`: fichajes nuevos y manuales intentan guardar empresa/centro.
- `fase-solicitudes-incidencias-empresa`: `LeaveRequest.company` e `Incident.company` con backfill.
- `fase-informes-empresa`: modelos y servicios de payroll/reports preparados para empresa.
- `fase-creacion-contexto-empresa`: creaciones nuevas y procesos automaticos guardan contexto multiempresa cuando existe.
- `fase-selectors-empresa`: primera capa de selectors por empresa y por empleado.
- `fase-filtros-listados-empresa-1`: empleados y turnos empiezan a usar selectors en listados administrativos.
- `fase-filtros-listados-empresa-2`: fichajes, solicitudes e incidencias usan selectors en listados principales.
- `fase-filtros-listados-empresa-3`: dashboard, reports, payroll y CSV filtran por empresa.
- `fase-permisos-acciones-empresa-1`: acciones administrativas de empleados y turnos usan querysets autorizados por empresa.
- `fase-permisos-acciones-empresa-2`: acciones administrativas de fichajes, solicitudes e incidencias usan querysets autorizados por empresa.
- `fase-forms-admin-empresa`: formularios administrativos sensibles filtran empleados por empresa.
- `fase-auditoria-company-null`: auditoria documental de `company=NULL` y `workplace=NULL`.
- `fase-cierre-admin-sin-company`: admin sin empresa deja de acceder a paneles operativos de cliente.
- `fase-hardening-company-not-null-plan`: plan tecnico inicial para endurecer `company` por fases.
- `fase-hardening-employeeprofile-company-not-null`: `EmployeeProfile.company` obligatorio con migracion unica y admin tecnico ajustado.
- `fase-hardening-shift-company-not-null`: `Shift.company` obligatorio con migracion unica y admin tecnico ajustado.
- `fase-hardening-leaverequest-company-not-null`: `LeaveRequest.company` obligatorio con migracion unica y admin tecnico ajustado.
- `fase-hardening-incident-company-not-null`: `Incident.company` obligatorio con migracion unica y admin tecnico ajustado.

## Hoja De Ruta Priorizada

### 0. `fase-cierre-baseline-post-incident`

- Objetivo: cerrar correctamente la fase ya implementada de `Incident.company`.
- Riesgo que elimina: empezar nuevas migraciones sobre una base local o branch no estabilizada.
- Componentes afectados: git status, migraciones `incidents`, documentacion de sesion.
- Dependencias: ninguna; es precondicion operativa.
- Cambios previstos: ninguno funcional; aplicar/verificar migracion en entornos objetivo y preparar commit si procede.
- Riesgos de migracion/datos: si `incidents.0007` no esta aplicada, produccion aun permite null a nivel DB.
- Tests: no nuevos; repetir smoke de `incidents` si se aplica migracion.
- Validaciones: `./.venv/bin/python manage.py showmigrations incidents`, `./.venv/bin/python manage.py migrate --plan`, `./.venv/bin/python manage.py test incidents`, `./.venv/bin/python manage.py check`.
- Done: worktree/base claramente estabilizados y `Incident.company` obligatorio en codigo y DB objetivo.

### 1. `fase-hardening-timeclockentry-company-not-null`

- Objetivo: hacer obligatorio `TimeClockEntry.company`.
- Riesgo que elimina: fichajes sin tenant, invisibles para admins y peligrosos para payroll/incidencias.
- Componentes afectados: `timeclock/models.py`, `timeclock/services.py`, `timeclock/forms.py`, `timeclock/admin.py`, tests de `timeclock`, `payroll`, `dashboard`, `incidents` y `reports` si procede.
- Dependencias: `EmployeeProfile.company`, `Shift.company` e `Incident.company` obligatorios.
- Cambios previstos: cerrar rutas con `company=None`, exponer `company` en admin, actualizar tests legacy y crear migracion unica.
- Riesgos de migracion/datos: `TimeClockEntry.company=NULL` o desalineado con empleado/turno bloquearia la migracion.
- Tests: reemplazar tests que aceptan fichajes sin empresa; anadir asserts en QR invalido, IP bloqueada y fichaje manual; probar `related_shift` de otro empleado.
- Validaciones: auditoria ORM previa, suite relacionada, suite global, `check`, `makemigrations --check --dry-run`, `git diff --check`.
- Done: `TimeClockEntry.company` no nullable y ningun path conocido puede crear fichajes sin empresa.

### 2. `fase-cierre-company-none-en-apis-internas`

- Objetivo: eliminar fallbacks globales reutilizables.
- Riesgo que elimina: futuros desarrolladores llamando forms/services con `company=None` y creando fugas.
- Componentes afectados: `scheduling/forms.py`, `timeclock/forms.py`, `payroll/services.py` y tests asociados.
- Dependencias: fase 1 para fichajes.
- Cambios previstos: `company=None` debe fallar cerrado o requerir una API global interna explicita.
- Riesgos de migracion/datos: ninguno directo; no requiere migracion.
- Tests: forms con `company=None` devuelven queryset vacio o error; payroll sin company falla explicitamente.
- Validaciones: tests `scheduling timeclock payroll reports`, `check`, `makemigrations --check --dry-run`, `git diff --check`.
- Done: no queda ningun servicio/form operativo que haga consulta global por omision.

### 3. `fase-hardening-monthlysummary-company-not-null`

- Objetivo: hacer obligatorio `MonthlyHoursSummary.company`.
- Riesgo que elimina: resumenes mensuales ambiguos o globales.
- Componentes afectados: `payroll/models.py`, `payroll/services.py`, `payroll/admin.py`, `payroll/tests.py`, `reports/tests.py`.
- Dependencias: fases 1 y 2.
- Cambios previstos: `company` obligatorio y `calculate_employee_summary()` siempre calculando en contexto de empresa.
- Riesgos de migracion/datos: summaries sin empresa o con empresa distinta del empleado.
- Tests: `company` requerido, coherencia employee/company y calculo worker/admin por empresa.
- Validaciones: auditoria summaries, tests payroll/reports/timeclock, suite global, `check`, `makemigrations --check --dry-run`, `git diff --check`.
- Done: no existen summaries sin empresa y el calculo no mezcla tenants.

### 4. `fase-hardening-payrolldraft-company-not-null`

- Objetivo: hacer obligatorio `PayrollDraft.company`.
- Riesgo que elimina: borradores de pre-nomina globales multiempresa.
- Componentes afectados: `payroll/models.py`, `payroll/services.py`, `payroll/admin.py`, `reports/views.py`.
- Dependencias: fases 2 y 3.
- Cambios previstos: `generate_payroll_draft()` exige company, admin expone/filtra company y se crea migracion unica.
- Riesgos de migracion/datos: drafts vacios o con lineas de varias empresas.
- Tests: generar draft sin company debe fallar; CSV sigue pasando company del admin.
- Validaciones: auditoria drafts null/mixtos, tests payroll/reports, suite global, `check`, `makemigrations --check --dry-run`, `git diff --check`.
- Done: ningun draft puede existir sin empresa.

### 5. `fase-hardening-payrolldraftline-company-not-null`

- Objetivo: hacer obligatoria y coherente la empresa de cada linea.
- Riesgo que elimina: lineas de pre-nomina cruzadas entre draft, empleado y empresa.
- Componentes afectados: `payroll/models.py`, `payroll/services.py`, admin inline y tests.
- Dependencias: fases 3 y 4.
- Cambios previstos: `PayrollDraftLine.company` obligatorio y validacion `line.company == draft.company == employee.company`.
- Riesgos de migracion/datos: lineas con empresa nula o distinta al draft/empleado.
- Tests: rechazo de linea cruzada y una linea por empleado/draft si se anade constraint.
- Validaciones: auditoria line null/mismatch, tests payroll/reports, suite global, `check`, `makemigrations --check --dry-run`, `git diff --check`.
- Done: no hay lineas sin empresa ni lineas fuera de la empresa del draft.

### 6. `fase-integridad-relaciones-operativas`

- Objetivo: reforzar invariantes cruzadas de dominio.
- Riesgo que elimina: registros coherentes por empresa pero enlazados a empleado/turno/fichaje equivocado.
- Componentes afectados: `timeclock/models.py`, `incidents/models.py`, `leaves/models.py`, `employees/models.py`.
- Dependencias: fases `company NOT NULL` de modelos operativos.
- Cambios previstos: validar `related_shift.employee`, `incident.shift.employee`, `incident.timeclock_entry.employee` y estados de revision/resolucion.
- Riesgos de migracion/datos: registros historicos con enlaces cruzados.
- Tests: casos negativos por relacion cruzada y estados inconsistentes.
- Validaciones: auditorias cross-table previas, tests por app, suite global, `check`, `makemigrations --check --dry-run`, `git diff --check`.
- Done: las entidades operativas no permiten asociaciones imposibles via modelo/form/admin.

### 7. `fase-admin-tenant-scope`

- Objetivo: aislar Django Admin por empresa o reservarlo a superuser tecnico.
- Riesgo que elimina: fugas/modificaciones cross-tenant desde admin.
- Componentes afectados: todos los `admin.py`, posiblemente un mixin compartido.
- Dependencias: campos `company` obligatorios en operativos y payroll.
- Cambios previstos: `get_queryset`, `formfield_for_foreignkey`, permisos y `company` readonly/asignada para admins de empresa.
- Riesgos de migracion/datos: staff existentes con permisos demasiado amplios.
- Tests: admin con empresa no ve objetos de otra; superuser conserva acceso global.
- Validaciones: tests admin por modelo, permisos manuales basicos, suite global, `check`, `makemigrations --check --dry-run`, `git diff --check`.
- Done: admin tecnico no puede romper aislamiento tenant accidentalmente.

### 8. `fase-workplace-operativo-y-qr-ip-por-centro`

- Objetivo: convertir `Workplace` en contexto real de planificacion/fichaje.
- Riesgo que elimina: QR/IP globales y centros inferidos de forma debil.
- Componentes afectados: `companies`, `employees`, `scheduling`, `timeclock`, `core`.
- Dependencias: empresa obligatoria y admin tenant-scoped.
- Cambios previstos: exponer centro en forms/admin, preservar centro al duplicar/copiar turnos y fichar contra QR/IP del centro.
- Riesgos de migracion/datos: empleados/turnos/fichajes sin centro o con centro incorrecto.
- Tests: QR/IP por centro, centro de turno preferente y centro obligatorio si aplica.
- Validaciones: auditoria workplace, tests timeclock/scheduling/companies, suite global, `check`, `makemigrations --check --dry-run`, `git diff --check`.
- Done: el fichaje ya no depende de `BusinessConfig` global para QR/IP operativo.

### 9. `fase-auditlog-y-documentacion-tenant-aware`

- Objetivo: auditar y documentar el sistema multiempresa real.
- Riesgo que elimina: trazabilidad global ambigua y documentacion que guia mal.
- Componentes afectados: `audit/models.py`, creacion de logs, `docs/*.md`, `README.md`.
- Dependencias: fases de company/workplace principales.
- Cambios previstos: anadir `company` nullable a audit log para eventos tenant y actualizar docs obsoletos.
- Riesgos de migracion/datos: logs antiguos sin empresa deben seguir validos.
- Tests: logs de fichaje/mantenimiento/reportes incluyen contexto cuando aplica.
- Validaciones: tests audit/core/timeclock, revision documental, suite global, `check`, `makemigrations --check --dry-run`, `git diff --check`.
- Done: la documentacion refleja el estado actual y los logs permiten investigacion por tenant.

## Plan Detallado De La Siguiente Fase

Fase: `fase-hardening-timeclockentry-company-not-null`

1. Auditoria previa:
- Consultar `TimeClockEntry.company=NULL`.
- Consultar `TimeClockEntry.employee.company != TimeClockEntry.company`.
- Consultar `TimeClockEntry.workplace.company != TimeClockEntry.company`.
- Consultar `TimeClockEntry.related_shift.company != TimeClockEntry.company`.
- Consultar `TimeClockEntry.related_shift.employee != TimeClockEntry.employee`.
- Si cualquier conteo es mayor que 0, parar y abrir fase de saneamiento de datos.

2. Proteccion de write paths:
- Cambiar `TimeClockEntry.clean()` para exigir `company`.
- Validar que `related_shift.employee == employee`.
- Mantener `workplace` nullable por ahora.
- Anadir `save()` con `full_clean()` en `TimeClockEntry`, salvo bloqueo tecnico demostrado.
- Cambiar `ManualTimeClockEntryForm(company=None)` a fail-closed.
- Exponer `company` en `TimeClockEntryAdmin`.

3. Migracion:
- Quitar `blank=True` y `null=True` de `TimeClockEntry.company`.
- Crear una unica migracion `timeclock/migrations/0006_alter_timeclockentry_company.py`.
- No tocar `TimeClockEntry.workplace`.

4. Tests:
- Reemplazar `test_entry_allows_empty_company_and_workplace_temporarily` por `test_entry_requires_company`.
- Reconducir tests de backfill/selector que crean entradas sin empresa.
- Anadir test de admin expone `company`.
- Anadir asserts de `company` en fichajes `INVALID_QR` y `BLOCKED_IP`.
- Anadir test negativo para `related_shift` de otro empleado.
- Actualizar fixtures de payroll que todavia crean fichajes sin empresa.

5. Validaciones:
- `./.venv/bin/python manage.py test timeclock incidents dashboard payroll reports`.
- `./.venv/bin/python manage.py test`.
- `./.venv/bin/python manage.py check`.
- `./.venv/bin/python manage.py makemigrations --check --dry-run`.
- `git diff --check`.
- Actualizar `docs/estado-sesion.md`.

6. Criterio exacto de cierre:
- `TimeClockEntry.company` obligatorio en modelo y migracion.
- Todos los paths normales crean fichajes con empresa.
- No quedan tests que traten `TimeClockEntry.company=NULL` como estado valido.
- Auditoria previa sin bloqueos.
- Suite completa en verde.

## Deudas Pendientes Importantes

- Ejecutar `fase-hardening-timeclockentry-company-not-null`.
- Endurecer payroll por fases: `MonthlyHoursSummary`, `PayrollDraft`, `PayrollDraftLine`.
- Cerrar `company=None` en APIs internas y formularios reutilizables.
- Decidir cuando endurecer `workplace` a no nullable por modelo.
- Mover configuracion QR/IP desde `BusinessConfig` global a `Workplace`.
- Decidir si hace falta panel operativo global interno para staff/superuser y como evitar que cree datos con `company=NULL`.
- Aislar Django Admin por tenant o reservarlo a superuser tecnico.
- Anadir contexto `company`/`workplace` a `AuditLog` cuando aplique.
- Actualizar o archivar documentacion obsoleta.
