# Estado de sesion

Fecha ultima actualizacion: 2026-10-16

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

- Fase cerrada: `fase-admin-tenant-scope` (fase 7), con Django Admin reservado a superusuario tecnico.
- Siguiente fase tecnica: `fase-workplace-operativo-y-qr-ip-por-centro` (fase 8).
- Auditar centros y su empresa en empleados, turnos y fichajes, y configuracion real de QR/IP antes de cambiar el contexto operativo. Elegir y probar el centro del turno/fichaje dentro de la empresa autorizada.
- Implementar centro en formularios/admin, preservarlo al copiar/duplicar turnos y validar fichajes contra Workplace; no endurecer centros a NOT NULL sin auditoria especifica.
- Antes de iniciar esta fase mas amplia, comprobar con el usuario el cupo restante: ha pedido aproximarse al 40%, pero el agente no puede consultar /status. Se ha solicitado el porcentaje durante el trabajo.
- La base local es nueva; cualquier base original que se recupere requiere copia y auditoria propias. No se han localizado ni migrado sus datos.

## Estado Actual Del Proyecto

- Fase cerrada: `fase-admin-tenant-scope`; 192 tests OK. Baseline anterior: `8f333d2` (integridad operativa).
- Baseline real de esta copia: `ccfe280` (`initial commit`), con la fase de Incident ya incluida. Las referencias a commits de septiembre que aparecen mas abajo son historicas.
- Cada fase cerrada dispone de su commit local con codigo, tests y este documento. Las bases externas/originales siguen pendientes de su propia auditoria y migracion.
- `EmployeeProfile.company` es obligatorio.
- `Shift.company` es obligatorio.
- `LeaveRequest.company` es obligatorio.
- `Incident.company` es obligatorio en codigo y migracion `incidents/migrations/0007_alter_incident_company.py`.
- `TimeClockEntry.company` es obligatorio en modelo y DB local con `timeclock.0006_alter_timeclockentry_company` aplicada. Su auditoria previa bloquea null e inconsistencias antes de cambiar el esquema.
- `MonthlyHoursSummary.company` es obligatorio y coherente con el empleado; `payroll.0005` aplicada localmente.
- `PayrollDraft.company` es obligatorio; `payroll.0006` aplicada. Los borradores con lineas no se pueden mover a una empresa incompatible.
- `PayrollDraftLine.company` es obligatorio y coincide con empleado y borrador; `payroll.0007` aplicada.
- `EmployeeProfile.primary_workplace`, `Shift.workplace` y `TimeClockEntry.workplace` siguen nullable y fuera del siguiente paso.
- Admin operativo sin `company` esta cerrado en vistas cliente.
- Staff/superuser sin perfil no tiene panel operativo global de cliente.
- Django Admin global queda reservado a superusuarios tecnicos activos y staff; los usuarios staff sin superuser no acceden, aunque tengan permisos de modelos.
- `BusinessConfig` sigue siendo global para QR/IP/mantenimiento.
- `docs/multiempresa-diagnostico.md` es historico/obsoleto y no debe usarse como estado actual.
- `docs/hardening-company-not-null-plan.md` es plan historico de la primera etapa; la fuente viva es este archivo.

## Ultima Auditoria De Datos

Auditoria de acceso local 2026-10-16 antes de fase 7: staff 0, staff sin superuser 0, superusers 0. La politica anterior permitia has_permission a cualquier usuario activo staff; la nueva exige tambien superuser. No se han creado, borrado ni modificado cuentas locales.

Auditoria ORM local 2026-10-16 antes de fase 6: Incident total 0, LeaveRequest total 0; diferencias de empresa con empleados, turno y fichaje 0; turno/empleado e incidencia/fichaje/empleado 0; empresa de revisor/resolutor 0; centro/empresa del empleado 0. Sin saneamiento ni cambio de esquema.

Auditoria ORM local 2026-10-16 previa a `payroll.0007`: lineas total 0, company=NULL 0, mismatch empleado/empresa 0 y borrador/empresa 0. Copia: `backups/shiftly-pre-payrollline-20261016-214723.sqlite3`. NOT NULL confirmado en las tres tablas de payroll.

Auditoria ORM local 2026-10-16 previa a `payroll.0006`: borradores total 0, company=NULL 0, vacios 0, empresas mixtas 0, mismatch linea/borrador 0 y empleado/borrador 0. Copia: `backups/shiftly-pre-payrolldraft-20261016-214431.sqlite3`. NOT NULL posterior confirmado.

Auditoria ORM local 2026-10-16 previa a `payroll.0005`: MonthlyHoursSummary total 0, company=NULL 0, mismatch employee/company 0. Base nueva; sin backfill adicional. Copia previa: `backups/shiftly-pre-monthlysummary-20261016-214213.sqlite3`. Esquema posterior NOT NULL confirmado por introspeccion.

Auditoria local 2026-10-16, previa a `timeclock.0006`, por ORM:

- Base nueva creada durante esta sesion; no corresponde a la base original de septiembre.
- `TimeClockEntry`: total 0, `company=NULL` 0, mismatch employee/company 0, workplace/company 0, related_shift/company 0, related_shift/employee 0.
- Sin datos que sanear ni backfill adicional necesario en esta base.
- `incidents.0007` verificada como aplicada antes de la nueva migracion.
- Tras aplicar migraciones: `company_id NOT NULL` y `workplace_id` nullable verificados por introspeccion SQLite.
- Copia de la base local previa a aplicar `timeclock.0006`: `backups/shiftly-pre-timeclock-company-20261016-213011.sqlite3` (ignorada por Git).

Auditoria historica de otra base, conservada sin presentar sus datos como actuales:

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

Fase `fase-admin-tenant-scope`, 2026-10-16: tests `core.test_admin_access payroll` 35 OK; suite completa 192 OK; check/makemigrations/diff OK. Sin migracion nueva; sin cambios pendientes de esquema.

Fase `fase-integridad-relaciones-operativas`, 2026-10-16: tests `employees leaves incidents payroll timeclock dashboard` 129 OK, nuevos tests `core.test_integrity` 9 OK; suite completa 185 OK; check/makemigrations/diff OK. Sin migraciones nuevas.

Fase `fase-hardening-payrolldraftline-company-not-null`, 2026-10-16: tests `payroll reports` 34 OK; suite global 176 OK; check/makemigrations/diff OK; `payroll.0007` aplicada e introspeccion NOT NULL de las tres tablas OK.

Fase `fase-hardening-payrolldraft-company-not-null`, 2026-10-16: tests `payroll reports` 28 OK; suite global 170 OK; check/makemigrations/diff OK; `payroll.0006` aplicada e introspeccion NOT NULL OK.

Fase `fase-hardening-monthlysummary-company-not-null`, 2026-10-16: tests `payroll reports timeclock dashboard` 69 OK; suite global 165 OK; check, makemigrations --check --dry-run y diff --check OK; `payroll.0005` aplicada e introspeccion NOT NULL OK.

Fase `fase-cierre-company-none-en-apis-internas`, 2026-10-16:

- Tests `scheduling timeclock payroll reports dashboard`: 95 OK; suite completa: 161 OK.
- `check`, `makemigrations --check --dry-run`, `git diff --check`: OK; sin migracion nueva.

Fase `fase-hardening-timeclockentry-company-not-null`, 2026-10-16:

- `./.venv/bin/python manage.py test timeclock incidents dashboard payroll reports --noinput`: 77 tests OK.
- `./.venv/bin/python manage.py test --noinput`: 154 tests OK.
- `./.venv/bin/python manage.py check`: OK.
- `./.venv/bin/python manage.py makemigrations --check --dry-run`: sin cambios pendientes.
- `./.venv/bin/python manage.py migrate --noinput`: OK; `incidents.0007` y `timeclock.0006` aplicadas en base local nueva.
- Introspeccion SQLite: empresa NOT NULL y centro nullable confirmados.
- Compilacion Python y `git diff --check`: OK.
- Las pruebas de migracion cubren conservacion de fichajes y centros, backfill historico y rechazo de los cinco casos de datos incompatibles antes de modificar el esquema.

Resultados historicos:

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

- Django Admin es exclusivamente tecnico: requiere is_active, is_staff e is_superuser, tanto en login como en cada vista incluida la de autocompletado y los endpoints personalizados registrados con admin_view.
- Los administradores de empresa usan vistas cliente limitadas a su empresa. Superusuarios tecnicos conservan acceso global explicito al admin.

- Incidencias solo se enlazan a turnos/fichajes del mismo empleado y empresa; save() valida los datos.
- Revisores y resolutores con perfil pertenecen a la empresa del registro. El tecnico sin perfil puede operar desde herramientas autorizadas.
- review()/resolve() bloquean la fila y comprueban que sigue pendiente antes de actuar; rechazan instancias obsoletas y revisiones repetidas. Las vistas devuelven mensajes de error sin sobrescribir datos.
- EmployeeProfile.company solo puede cambiar mientras no exista historial operativo propio o de revision/resolucion; save() valida el perfil y protege ese historial.

- PayrollDraftLine exige empresa en modelo y DB, coincidente con empleado y borrador. Admin inline muestra company de solo lectura y no permite altas manuales incompletas.

- PayrollDraft exige empresa en modelo y DB y rechaza cambios de empresa incompatibles con sus lineas/empleados. Los borradores vacios con empresa conocida siguen siendo validos.

- MonthlyHoursSummary exige empresa en modelo y DB; save() valida la coincidencia con employee.company.

- Los cuatro servicios de payroll exigen empresa guardada explicita; los calculos de empleado rechazan otra empresa antes de consultar datos.
- ShiftForm y ManualTimeClockEntryForm no muestran ni aceptan empleados sin contexto de empresa, tambien al editar.
- El servicio de fichajes abiertos exige un queryset de empleados explicito; no consulta toda la plataforma por omision.

- Admin con `company` mantiene gestion operativa limitada a su empresa.
- Admin sin `company` ya no puede usar paneles operativos de cliente.
- Trabajadores mantienen comportamiento propio.
- Selectors por empresa fallan cerrado con `company=None` en empleados, turnos, fichajes, solicitudes, incidencias y summaries.
- `EmployeeProfile.company` no permite `null=True` ni `blank=True`.
- `Shift.company` no permite `null=True` ni `blank=True`.
- `LeaveRequest.company` no permite `null=True` ni `blank=True`.
- `Incident.company` no permite `null=True` ni `blank=True`.
- `TimeClockEntry.company` no permite `null=True` ni `blank=True`; `save()` ejecuta `full_clean()` en altas y actualizaciones.
- `TimeClockEntry.related_shift.employee` debe coincidir con `TimeClockEntry.employee`.
- El formulario manual de fichajes no consulta empleados globalmente si falta empresa.
- Django Admin expone `company` en `EmployeeProfile`, `Shift`, `LeaveRequest` e `Incident` para no romper creacion tecnica.

## Invariantes Pendientes

- `workplace` todavia no es una invariante fuerte.
- QR/IP por fichaje siguen en `BusinessConfig` global y deben moverse a `Workplace` en una fase posterior.
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
- `fase-hardening-timeclockentry-company-not-null`: empresa obligatoria en fichajes, guardas de migracion, validacion al guardar, formulario manual cerrado sin empresa y 154 tests OK; aplicada en base local nueva.
- `fase-cierre-company-none-en-apis-internas`: formularios y servicios sin fallback global, llamadas worker explicitas y 161 tests OK.
- `fase-hardening-monthlysummary-company-not-null`: migracion `payroll.0005`, validacion del modelo/admin y 165 tests OK.
- `fase-hardening-payrolldraft-company-not-null`: migracion `payroll.0006`, validacion al guardar y 170 tests OK.
- `fase-hardening-payrolldraftline-company-not-null`: migracion `payroll.0007`, coherencia de las lineas y 176 tests OK.
- `fase-integridad-relaciones-operativas`: relaciones y cambios de empresa protegidos, acciones pendientes verificadas y 185 tests OK.
- `fase-admin-tenant-scope`: opcion de reserva a superusuario tecnico, acceso/login centralizado y 192 tests OK.

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

## Plan Detallado Conservado De La Fase De Fichajes (Cerrada)

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

- Ejecutar `fase-workplace-operativo-y-qr-ip-por-centro` tras revisar el cupo restante con el usuario.
- Decidir cuando endurecer `workplace` a no nullable por modelo.
- Mover configuracion QR/IP desde `BusinessConfig` global a `Workplace`.
- Decidir si hace falta panel operativo global interno para staff/superuser y como evitar que cree datos con `company=NULL`.
- Anadir contexto `company`/`workplace` a `AuditLog` cuando aplique.
- Actualizar o archivar documentacion obsoleta.

## Sesion 2026-10-16 - Preparacion Inicial (Historico; Cierre A Continuacion)

### Cambios Preparados

- `TimeClockEntry.company` pierde `null=True` y `blank=True`; la obligatoriedad la valida `full_clean()`, tambien ejecutado desde `save()` para cubrir creacion y correcciones.
- `TimeClockEntry.clean()` rechaza un `related_shift` que pertenezca a otro empleado, incluso si ambos empleados son de la misma empresa.
- El servicio de contexto rechaza empleados sin empresa antes de crear fichajes; el servicio de creacion utiliza el `save()` validado del modelo.
- `ManualTimeClockEntryForm` devuelve queryset vacio sin empresa y asigna la empresa autorizada a la instancia antes de la validacion del modelo.
- Django Admin incluye empresa en listado/filtros/autocompletado; su formulario exige empresa.
- Una unica migracion nueva, `timeclock.0006_alter_timeclockentry_company`, ejecuta una auditoria sin escrituras antes de `AlterField`: null, employee/company, workplace/company, related_shift/company y related_shift/employee. Si falla, aborta con conteos, sin asignar empresas por defecto ni corregir datos silenciosamente.
- La migracion depende de las fases previas de EmployeeProfile, Shift e Incident para garantizar el orden de aplicacion.
- Fixtures de timeclock/payroll actualizadas para usar empresas coherentes. Los tests actuales ya no tratan company=NULL como valido.
- Los tests de backfill usan modelos y esquema historicos con `MigrationExecutor`, donde company=NULL si era representable. Cubren preservacion de datos y bloqueo de la nueva migracion ante cada inconsistencia.
- Se mantienen `workplace` nullable, configuracion global, QR/IP, templates y diseno visual sin cambios.

### Entorno Y Datos

- Worktree inicialmente limpio, baseline `ccfe280`.
- No habia `.venv` ni `db.sqlite3` en esta copia; no se ha localizado ni modificado la base original.
- `.venv` creado con Python 3.13. Instalacion de requirements intentada y fallida por resolucion de red bloqueada; Django sigue sin instalarse.
- No se ha creado una base vacia para presentarla como auditoria de datos existentes.
- Se ha solicitado al usuario instalar las dependencias desde un terminal con red mientras se preparaba el codigo.

### Verificaciones Y Cierre Pendiente

- Compilacion Python de todas las apps: OK.
- `git diff --check`: OK.
- Revision AST de fixtures actuales: todos los `TimeClockEntry.objects.create()` especifican empresa.
- Auditoria ORM, migraciones, `manage.py check`, `makemigrations --check --dry-run`, tests relacionados y suite completa: PENDIENTES por falta de Django.
- Sin commit de cierre: la fase no debe marcarse terminada hasta validar y aplicar la migracion en el entorno disponible. La base original requerira su propia auditoria/copia/aplicacion si se recupera posteriormente.

## Cierre 2026-10-16 - Fichajes Con Empresa Obligatoria

- El usuario ha instalado las dependencias desde su terminal; verificado Django 5.2.15, asgiref 3.11.1 y sqlparse 0.5.5 en `.venv`.
- Base SQLite local nueva creada y migraciones previas de employees/scheduling/incidents aplicadas. Auditoria ORM previa de fichajes: total 0 y todos los conteos de null/inconsistencias 0.
- Tests relacionados: 77 OK. Suite completa: 154 OK. `check`, `makemigrations --check --dry-run`, compilacion y `git diff --check`: OK.
- Copia local realizada y todas las migraciones aplicadas, incluida `timeclock.0006`; introspeccion confirma empresa NOT NULL y centro todavia nullable.
- Fase cerrada para el codigo y el entorno local disponible. No se ha accedido a la base original ni se ha acreditado su estado; si aparece, hacer copia y auditar antes de migrar.
- Commit local de cierre: mensaje `fase-hardening-timeclockentry-company-not-null`; sin push.
- Siguiente fase: `fase-cierre-company-none-en-apis-internas`. No se ha implementado ninguna fase posterior.

## Cierre 2026-10-16 - APIs Internas Sin Empresa

- Auditadas todas las llamadas a ShiftForm, formulario manual y servicios de calculo/generacion de payroll. Reportes ya pasaban empresa; dashboard del trabajador y pagina de horas ahora tambien la pasan.
- Payroll rechaza empresa omitida, None, sin guardar o empleado de otra empresa. Todas las consultas de resumen/horas filtran empresa incondicionalmente. No hay API global implicita.
- Eliminado el fallback global de empleados en ShiftForm y del servicio employees_with_open_clock_entries. La auditoria detecto este ultimo fuera de los tres archivos inicialmente previstos; su unico llamador ya pasa un queryset autorizado.
- Formularios sin empresa fallan cerrado en altas y ediciones sin borrar company de la instancia existente. Pruebas de no escritura, aislamiento, empresas invalidas y pantalla de horas incluidas.
- Tests relacionados: 95 OK; globales: 161 OK; check/makemigrations/diff: OK. No se han cambiado campos ni aplicado migraciones en esta fase.
- Commit local: `fase-cierre-company-none-en-apis-internas`. Siguiente: MonthlyHoursSummary.company NOT NULL, con auditoria previa.

## Cierre 2026-10-16 - Empresa Obligatoria En Resumenes Mensuales

- Auditoria previa ORM: 0 resumenes, 0 null y 0 discrepancias con empleado. No se ha usado la auditoria historica como prueba del estado actual.
- Modelo exige company y valida employee/company en cada save; admin muestra y permite seleccionar empresa.
- Una migracion `payroll.0005` valida los datos sin modificarlos antes de imponer NOT NULL; depende de fichajes ya endurecidos.
- Tests antiguos de backfill reconducidos a modelos/esquema historicos con MigrationExecutor. Se comprueba backfill y preservacion de summary/draft/line, rechazo de null y discrepancias antes del DDL, y restricciones del modelo y DB.
- Tests relacionados: 69 OK; suite: 165 OK; check/makemigrations/diff OK. Copia local previa realizada; migracion aplicada y NOT NULL verificado en SQLite.
- PayrollDraft y PayrollDraftLine siguen nullable hasta sus fases. No se han cambiado centros ni QR/IP ni templates.
- Commit local: `fase-hardening-monthlysummary-company-not-null`. Siguiente: PayrollDraft.company NOT NULL.

## Cierre 2026-10-16 - Empresa Obligatoria En Borradores

- Auditoria ORM previa: 0 borradores, null, vacios, mixtos y discrepancias linea/borrador o empleado/borrador. Sin saneamiento necesario en la base local nueva.
- PayrollDraft exige company; save() valida datos y evita mover un borrador existente fuera de la empresa de sus lineas/empleados. Admin muestra empresa con autocompletado.
- Migracion unica `payroll.0006` con auditoria previa sin escrituras: rechaza null y relaciones cruzadas, sin adivinar empresas ni reescribir datos.
- Pruebas con esquema historico: conserva borradores vacios y con lineas; bloquea borradores ambiguos o cruzados antes del DDL. Campos de linea siguen nullable hasta fase 5.
- Tests relacionados: 28 OK; suite: 170 OK; check/makemigrations/diff OK. Copia previa realizada, migracion aplicada y NOT NULL confirmado en SQLite.
- Commit local: `fase-hardening-payrolldraft-company-not-null`. Siguiente: PayrollDraftLine.company NOT NULL.

## Cierre 2026-10-16 - Empresa Obligatoria En Lineas De Pre-Nomina

- Auditoria ORM previa: 0 lineas, null o diferencias con employee.company/draft.company.
- Modelo exige company y valida ambas relaciones en cada save, tambien en actualizaciones. El servicio genera lineas desde empresa explicita ya validada.
- Inline de Django Admin muestra empresa de solo lectura y no permite altas manuales sin empleado/contexto; los errores cruzados usan errores generales compatibles con el inline.
- Migracion unica `payroll.0007` audita antes de imponer NOT NULL y rechaza null o diferencias sin reescribir historico. No se ha anadido una constraint de duplicados ni modificado su semantica.
- Tests historicos comprueban preservacion de horas, observaciones, empleado y borrador, y rechazo de cada inconsistencia antes del DDL. Tests actuales cubren modelo, DB y POST real del admin con intento de cambio de empresa: devuelve errores, no 500, y conserva datos.
- Tests relacionados: 34 OK; globales: 176 OK; check/makemigrations/diff OK. Copia previa realizada, migracion aplicada y NOT NULL confirmado en las tres tablas de payroll.
- Commit local: `fase-hardening-payrolldraftline-company-not-null`. Siguiente: integridad de relaciones operativas.

## Cierre 2026-10-16 - Integridad De Relaciones Operativas

- Auditoria previa ORM local sin relaciones cruzadas ni datos que sanear. No se ha modificado el esquema.
- Incident valida empleado de turno/fichaje; Incident y LeaveRequest validan empresa del resolutor/revisor cuando existe perfil y ejecutan full_clean() al guardar.
- review()/resolve() leen el estado persistido con select_for_update dentro de una transaccion. Rechazan registros ya procesados/cancelados o instancias obsoletas. Las vistas muestran ValidationError sin 500 ni escrituras parciales. En SQLite select_for_update no aporta bloqueo de fila; la prueba acredita rechazo de instancias obsoletas, no concurrencia real entre procesos.
- Decidido proteger historico al cambiar EmployeeProfile.company: se permite antes de actividad; se bloquea con turnos, fichajes, solicitudes, incidencias, resumenes, lineas o acciones de revision/resolucion. No se ha modelado traslado de historico entre empresas.
- Estados aprobados importados sin revisor siguen representables: no se exige completar datos historicos no disponibles. La transicion por API si exige estado pendiente y guarda actor/fecha.
- Tests de payroll que simulan datos historicos corruptos usan bulk_create de forma explicita; las rutas normales de guardado ya rechazan esas discrepancias.
- Tests existentes relacionados: 129 OK; nuevos de integridad: 9 OK; suite global: 185 OK; check/makemigrations/diff OK. Se corrigio la carga del POST de una prueba nueva para enviar un formulario vinculado antes de la regresion completa.
- Commit local: `fase-integridad-relaciones-operativas`. Siguiente: aislamiento de Django Admin.

## Cierre 2026-10-16 - Administrador Global Reservado A Tecnicos

- Elegida la opcion prevista en la fase 7 de reservar Django Admin a superusuario tecnico; no se ha habilitado un admin global para cuentas de empresa.
- Configuracion mediante AdminConfig.default_site y TechnicalAdminSite.has_permission, sin monkeypatch ni registros de modelos duplicados. Login especializado rechaza staff sin superuser con error visible.
- La barrera central cubre cada modelo registrado, GET/POST de altas/cambios/borrados, historial, autocompletado y endpoint personalizado de QR. Los permisos de modelos no la evitan.
- Auditoria previa: ninguna cuenta staff/superuser en la base local nueva. No se han alterado cuentas existentes. README documenta requisitos y createsuperuser para entornos nuevos.
- Tests prueban todos los modelos registrados con staff que tiene todos los permisos; prueban tambien staff sin perfil, login denegado, ausencia de escrituras, QR sin cambios, acceso global tecnico y acceso normal de administrador de empresa limitado a su empresa.
- Tests relacionados: 35 OK; globales: 192 OK; check/makemigrations/diff OK. Sin cambios de esquema.
- Commit local: `fase-admin-tenant-scope`. Siguiente: Workplace operativo y QR/IP por centro; pendiente conocer el cupo de uso para respetar el limite solicitado por el usuario.
