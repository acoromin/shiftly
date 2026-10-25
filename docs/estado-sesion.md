# Estado de sesion

Fecha ultima actualizacion: 2026-10-25

Este archivo es la fuente operativa principal del proyecto. Si el usuario dice `mira estado-sesion`, leer este archivo primero, comprobar el estado real del repo y actuar segun `Siguiente Accion Operativa`.

El orden vigente de desarrollo y sus criterios de cierre estan en [plan-desarrollo.md](plan-desarrollo.md). Este archivo conserva el estado ejecutado y el historial. Las instrucciones antiguas de ejecucion se han retirado; el unico orden vigente es D1–D9.

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

- Etapa cerrada localmente: **D1 — Permisos y configuracion global** (`f1541e4`).
- Etapa activa: **D2 — Fichaje, red y credenciales de centro**. Politica de IP, QR nuevo, transicion de QR antiguos y limites de intentos implementados localmente; [guia operativa](seguridad-fichaje-d2.md).
- Falta para cerrar D2: ensayo del proxy y de QR impreso/login en staging, inspeccion de logs y confirmacion de aislamiento de acceso directo. No se ha localizado un staging ni hay datos de proxy confirmados. No declarar D2 cerrada sin esa evidencia.
- Siguiente tarea: localizar o preparar staging/proxy, confirmar sus CIDR confiables y completar la validacion integrada descrita en `docs/seguridad-fichaje-d2.md`. Si el entorno no existe, D2 sigue abierta; no empezar D3 anticipadamente.
- La antigua fase 9 de AuditLog queda incorporada a D6. Seguir el orden D1–D9.
- La base local es nueva; cualquier base original que se recupere requiere copia y auditoria propias. No se han localizado ni migrado sus datos.

## Estado Actual Del Proyecto

- Etapa cerrada localmente: D1. Baseline de entrada: `9985608` (fase 8). Matriz vigente en [permisos-configuracion.md](permisos-configuracion.md).
- D1 tiene el commit `f1541e4`. D2 tiene codigo y pruebas locales, con validacion de staging pendiente. Consultar `git status -sb` y `origin/main` al retomar para comprobar el estado de publicacion; ningun cambio de D2 se ha desplegado en staging o produccion.
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
- `EmployeeProfile.primary_workplace`, `Shift.workplace` y `TimeClockEntry.workplace` siguen nullable; los formularios operativos permiten elegir centros activos de la empresa autorizada.
- Admin operativo sin `company` esta cerrado en vistas cliente.
- Staff/superuser sin perfil no tiene panel operativo global de cliente.
- Django Admin global queda reservado a superusuarios tecnicos activos y staff; los usuarios staff sin superuser no acceden, aunque tengan permisos de modelos.
- `BusinessConfig` es global para mantenimiento y solo lo edita un tecnico activo, staff y superusuario. Nombre y tolerancia operativos pertenecen a `Company`; QR/IP a `Workplace`. Los campos antiguos permanecen para compatibilidad y no autorizan fichajes. `companies.0004` aplicada localmente.
- Configuracion de empresa en `/configuracion/empresa/`, limitada a la empresa del perfil. Perfiles inactivos o empresas inactivas no acceden a las rutas cliente; un tecnico conserva las herramientas globales de recuperacion.
- Riesgos abiertos: politica D2 de IP/QR pendiente de validacion en staging; consultas recalculan/persisten resumenes y reinician horas extra aprobadas; concurrencia de fichajes sin acreditar. El acceso de administradores de empresa al mantenimiento global queda corregido en D1.
- Los documentos de planificacion obsoletos se han eliminado; sus versiones originales se conservan en Git.
- La [auditoria historica de datos](archivo/auditoria-company-null.md) se conserva en `docs/archivo/` como evidencia, sin instrucciones para retomar el trabajo.

## Ultima Auditoria De Datos

D2, 2026-10-25: una empresa, un centro activo, cero centros con QR y cero fichajes en la base local. Copia SQLite verificada: `backups/shiftly-pre-d2-20261025-215449.sqlite3`. Aplicadas `companies.0005` y `core.0004`: el centro conserva estado/credencial, tiene un UUID publico unico; contador de intentos vacio. Sin acceso a la base original ni staging.

D1, 2026-10-22: una empresa activa (Xarlot), cero perfiles, cero staff/superusuarios y ninguna fila BusinessConfig. Copia verificada con `PRAGMA integrity_check`: `backups/shiftly-pre-d1-20261022-222641.sqlite3`. Aplicada `companies.0004`: misma empresa/nombre/estado, tolerancia 5; sigue sin configuracion global. No se crean cuentas ni se reasignan empresas.

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

D2 (avance local), 2026-10-25: regresion completa final **240 pruebas OK** sobre SQLite (138,845 s); `check`, `makemigrations --check --dry-run`, `migrate --plan`, enlaces Markdown y `git diff --check` OK. `companies.0005` y `core.0004` aplicadas localmente tras copia verificada. D2 sigue abierta por la prueba integrada de staging.

D1, 2026-10-22: `core dashboard companies`, 52 OK; migraciones de timeclock y companies, 4 OK; regresion completa final, **221 pruebas OK** sobre SQLite (89,719 s). `check`, `makemigrations --check --dry-run`, enlaces Markdown y `git diff --check` OK. `companies.0004` aplicada y verificada tras copia local.

Fase `fase-workplace-operativo-y-qr-ip-por-centro`, 2026-10-22: tests relacionados 124 OK antes de cerrar los casos de QR/turno adicionales; suite completa 203 OK; `check`, `makemigrations --check --dry-run` y `git diff --check` OK; `companies.0003` aplicada a la base local.

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

## Registro Historico De Sesiones

Los siguientes cierres reflejan lo que se hizo y se decidio en cada fecha. Las menciones historicas a siguientes fases no son instrucciones vigentes; para continuar, usar exclusivamente `Siguiente Accion Operativa` y [plan-desarrollo.md](plan-desarrollo.md).

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

## Cierre 2026-10-22 - Centro Operativo Y QR/IP Por Centro

- Antes de esta fase se subieron a `origin/main` los siete commits locales de las fases anteriores (`ccfe280..2241590`); el usuario autorizo continuar con fase 8.
- Auditoria ORM local: 1 empresa, 1 centro, 0 empleados, 0 turnos, 0 fichajes; 0 QR e IP configurados tanto en Workplace como en BusinessConfig. Discrepancias centro/empresa en empleados, turnos y fichajes: 0. La base original externa sigue sin localizarse.
- Formularios de empleado, turno y fichaje manual exponen centros activos de la empresa autorizada. Admin tecnico muestra los centros en empleado, turno y fichaje; puede configurar IP y generar QR por centro. El comando `setup_xarlot_clock` exige `--workplace-id`.
- Los turnos nuevos admiten centro explicito; duplicar y copiar semana preservan el centro original aunque difiera del centro principal del empleado. El fichaje por QR detecta el turno activo y exige su centro si existe. En ausencia de un turno con centro, el QR identifica un unico centro activo de la empresa. Una IP distinta, un QR de otra empresa, un QR duplicado entre centros o un centro inactivo no autorizan el fichaje.
- La configuracion global de QR/IP se ha retirado de los formularios/admin operativos y no participa en la autorizacion. `companies.0003` copia credenciales globales antiguas cuando solo hay un centro y este carece de ellas; con varios centros no adivina el destino. Los campos antiguos de BusinessConfig siguen en el esquema para compatibilidad historica.
- No se ha impuesto `workplace NOT NULL` ni cambiado el esquema de sus tres relaciones. Copia previa local: `backups/shiftly-pre-workplace-20261022.sqlite3`; migracion `companies.0003` aplicada.
- Pruebas especificas de aislamiento de centros, QR/IP por centro, turno activo, copia/duplicacion y migracion de credenciales incorporadas. Suite completa: 203 tests OK; `check`, `makemigrations --check --dry-run` y `git diff --check` OK.
- Siguiente fase: `fase-auditlog-y-documentacion-tenant-aware`.

## Revision 2026-10-22 - Plan De Producto Y Escalabilidad

- Creado `docs/plan-desarrollo.md` por peticion del usuario, con el objetivo de preparar un producto fiable y escalable y validar su utilidad mediante un piloto.
- Orden vigente: D1 permisos globales; D2 IP/proxy y QR; D3 consultas y calculos de horas; D4 PostgreSQL/entornos/CI; D5 concurrencia; D6 auditoria e historico; D7 recorrido de cliente; D8 operacion/capacidad; D9 piloto y decision de lanzamiento.
- Cada etapa incluye dependencias y evidencia de cierre. Los objetivos de carga, latencia y recuperacion son propuestas pendientes de medicion; no se presentan como capacidad actual.
- Actualizados README y las secciones operativas de esta bitacora. La hoja antigua y los cierres anteriores se conservan como historico.
- Cambio exclusivamente documental; sin cambios de codigo, datos o migraciones. Revision de enlaces locales y `git diff --check` correctos. No se ha repetido la suite funcional por este cambio.
- Siguiente tarea concreta: D1, reproducir y cerrar el permiso que permite a un administrador de empresa activar mantenimiento global.

## Limpieza 2026-10-22 - Una Sola Hoja De Ruta

- Eliminados los dos documentos obsoletos de planificacion y diagnostico multiempresa, a peticion del usuario.
- Retiradas de esta bitacora la hoja de ruta antigua, el plan detallado de fichajes cerrado y las listas duplicadas de pendientes. Se conservan los cierres, resultados y auditorias historicas.
- Archivada la auditoria antigua en `docs/archivo/`, identificada como evidencia de otra fecha y sin sus recomendaciones de siguientes fases.
- `docs/plan-desarrollo.md` es el unico plan vigente. Esta bitacora registra avance y siguiente tarea: D1, permisos y configuracion global.
- Cambio documental; enlaces y diff revisados.

## Cierre D1 — Permisos y configuracion global (2026-10-22)

- Reproducido el fallo original mediante una prueba: un administrador de empresa obtenia 302 y activaba mantenimiento global; se esperaba 403. Corregido antes del cierre.
- `/configuracion/` y Django Admin comparten el requisito tecnico: usuario autenticado, activo, staff y superusuario. Los administradores de empresa no pueden consultar ni modificar el formulario global, tampoco enviando POST manuales.
- Nueva pantalla `/configuracion/empresa/`: nombre y tolerancia exclusivamente de la empresa del perfil. Ignora identificadores ajenos y campos de plataforma enviados por el cliente. Navegacion y banner distinguen las capacidades.
- La tolerancia del panel pasa a `Company.clock_tolerance_minutes`. Migracion `companies.0004` ensayada con valor global personalizado para varias empresas y con ausencia de configuracion global; aplicada localmente tras copia verificada. Se conservan los campos globales antiguos para compatibilidad historica.
- Perfiles inactivos o sin empresa y empresas inactivas quedan bloqueados en rutas cliente. Se mantiene el cierre de sesion y el acceso tecnico a herramientas globales de recuperacion. Un tecnico sin perfil no obtiene permisos de administrador de empresa.
- Middleware y contexto de mantenimiento consultan sin crear una fila `BusinessConfig` al abrir pantallas cliente o denegar un acceso.
- Matriz de roles, inventario de rutas, propiedad de ajustes y limites documentados en `docs/permisos-configuracion.md`. Es una referencia tecnica; `docs/plan-desarrollo.md` sigue siendo el unico plan vigente.
- La primera regresion completa detecto dos errores en fixtures de `timeclock.test_migrations`: usaban un estado historico de Company incompatible con el esquema que seguia aplicado. Se corrigio la preparacion para respetar las migraciones actuales de las otras apps, manteniendo el retroceso de timeclock y sus aserciones de integridad.
- Pruebas focalizadas: `core dashboard companies`, 52 OK; tras el ajuste del fixture, `timeclock.test_migrations companies.test_migrations`, 4 OK.
- Comprobaciones: `check` sin incidencias; `makemigrations --check --dry-run` sin cambios; enlaces locales Markdown correctos. Recorridos de configuracion verificados con peticiones HTTP de integracion y comprobacion del HTML, sin validacion visual en navegador.
- Limites: validacion local sobre SQLite. No acredita produccion ni concurrencia PostgreSQL; no hay despliegue ni push de este cierre. Base original pendiente de localizar/auditar. D2–D9 conservan sus criterios de salida.
- Siguiente sesion: leer el inicio de esta bitacora, comprobar Git y comenzar D2 por la obtencion de IP y la prueba de `X-Forwarded-For` falsificado. No se ha empezado D2 hoy.

- Regresion completa final tras la correccion: **221 pruebas OK**, 89,719 s, SQLite; `git diff --check` OK. Commit local de cierre: `fase-permisos-plataforma-y-empresa` (incluye la consolidacion documental autorizada en esta sesion).

## Avance D2 — 2026-10-25

- Reproducido con una prueba el fallo de IP: una conexion directa desde `198.51.100.99` con `X-Forwarded-For: 203.0.113.10` obtenia fichaje valido. La politica nueva ignora esa cabecera salvo que el peer pertenezca a `TRUSTED_PROXY_CIDRS`.
- Nueva seleccion por `Workplace.qr_public_id` UUID, con busqueda por empresa/centro activo antes de verificar un unico hash. Sin ID se conserva el recorrido anterior mientras `CLOCK_ALLOW_LEGACY_QR=1`; la retirada operativa esta descrita en `docs/seguridad-fichaje-d2.md`.
- URLs nuevas con secreto en fragmento; captura en navegador, envio POST e inicio de sesion con `next` POST. Admin tecnico y comando emiten el nuevo formato. Accion Admin de revocacion inmediata y regeneracion existente para rotacion.
- Contadores en DB para login normal/Admin y fichaje, con comando de limpieza diaria. Son limites locales; medir su comportamiento con varios procesos y PostgreSQL en D4–D5.
- La guia D2 documenta el contrato de proxy, la IP WiFi, el tratamiento de secretos, impresion/rotacion/revocacion, la transicion de QR antiguos y los limites de presencia. D2 sigue abierta mientras falte prueba de proxy/QR impreso/logs en staging.
- Pruebas focalizadas: `timeclock.tests companies.tests`, 63 OK tras el cambio de QR; `companies.test_qr_migration`, 1 OK; `core.test_throttling timeclock.tests.ClockThrottlingTests`, 4 OK; recorrido login/POST/QR/migracion, 6 OK; generacion/revocacion QR y prioridad POST, 3 OK. `check`, `makemigrations --check --dry-run` y `migrate --plan` sin incidencias. La regeneracion muestra secretos una sola vez en una respuesta `no-store`, sin mensaje/cookie. La regresion completa final fue de **240 pruebas OK** en 138,845 s sobre SQLite; la verificacion con proxy real e impresion/logs de QR sigue pendiente.
