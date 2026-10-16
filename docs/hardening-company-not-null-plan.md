# Plan hardening company NOT NULL

Fecha: 2026-07-03

Fase: `fase-hardening-company-not-null-plan`

Commit base: `5f42862` (`fase-cierre-admin-sin-company`)

## Resumen Ejecutivo

- Fase documental y de analisis para preparar el endurecimiento de `company` a obligatorio.
- No se han cambiado modelos ni `null=True`.
- No se han creado migraciones.
- No se han cambiado rutas funcionales, templates, diseno visual, `BusinessConfig` ni QR/IP por centro.
- Los datos actuales no bloquean `company NOT NULL`: no hay registros con `company=NULL` en los modelos revisados.
- Tampoco hay `workplace=NULL` o `primary_workplace=NULL` en los datos actuales auditados con centro.
- No se han detectado inconsistencias entre `record.company` y relaciones como `employee.company`, `shift.company`, `timeclock_entry.company`, `draft.company` o `workplace.company`.
- La recomendacion es aplicar hardening en fases pequenas, empezando por `EmployeeProfile.company`.

## Estado Actual De Datos

| Modelo | Total | company_NULL | workplace_NULL / primary_workplace_NULL | Inconsistencias |
| --- | ---: | ---: | ---: | ---: |
| `EmployeeProfile` | 1 | 0 | 0 | 0 |
| `Shift` | 0 | 0 | 0 | 0 |
| `TimeClockEntry` | 2 | 0 | 0 | 0 |
| `LeaveRequest` | 0 | 0 | - | 0 |
| `Incident` | 0 | 0 | - | 0 |
| `MonthlyHoursSummary` | 1 | 0 | - | 0 |
| `PayrollDraft` | 1 | 0 | - | 0 |
| `PayrollDraftLine` | 1 | 0 | - | 0 |

## Riesgo Por Modelo

| Orden | Modelo | Riesgo | Motivo principal |
| ---: | --- | --- | --- |
| 1 | `EmployeeProfile.company` | Medio | Es la fuente de empresa para empleados y admins; Django admin no expone `company` en el formulario actual. |
| 2 | `Shift.company` | Medio | Las rutas cliente asignan contexto, pero los tests y admin todavia permiten creacion sin empresa. |
| 3 | `LeaveRequest.company` | Bajo-Medio | La ruta cliente asigna empresa desde el perfil; depende de que `EmployeeProfile.company` ya sea obligatorio. |
| 4 | `Incident.company` | Medio | Hay varias rutas automaticas de creacion desde dashboard y fichajes pendientes. |
| 5 | `TimeClockEntry.company` | Medio | El servicio de fichaje asigna contexto, pero workers sin empresa y admin/manual legacy deben quedar cerrados antes. |
| 6 | `MonthlyHoursSummary.company` | Medio | `calculate_employee_summary()` acepta `company=None` y deriva desde `employee.company`. |
| 7 | `PayrollDraft.company` | Alto | `generate_payroll_draft()` acepta `company=None`; debe cerrarse antes de `null=False`. |
| 8 | `PayrollDraftLine.company` | Medio-Alto | Deriva de `summary.company`, `employee.company` o `draft.company`; depende de cerrar `PayrollDraft.company`. |

## Rutas De Creacion Revisadas

| Modelo | Rutas revisadas | Estado actual |
| --- | --- | --- |
| `EmployeeProfile` | `employees.views.employee_create()` con `EmployeeForm`; `employees.admin.EmployeeProfileAdmin`; tests y backfill previo. | La vista cliente asigna `current_profile.company`; admin no expone `company` y necesita revision antes de endurecer. |
| `Shift` | `scheduling.views.create_shift()`, `edit_shift()`, `duplicate_shift()`, `copy_previous_week()`; `ShiftForm`; `ShiftAdmin`; tests y backfill previo. | Las vistas aplican contexto desde empleado/fallback; admin guarda auditoria pero no asigna empresa. |
| `TimeClockEntry` | `timeclock.services.create_timeclock_entry()`, `attempt_clock()`, `apply_timeclock_entry_context()`; `timeclock.views.manual_create()` y `correct_entry()`; `TimeClockEntryAdmin`; tests y backfill previo. | Fichajes nuevos y manuales aplican contexto; correcciones no cambian empresa; admin necesita revision. |
| `LeaveRequest` | `leaves.views.create_request()`; `review_request()`; `LeaveRequestAdmin`; tests y backfill previo. | La creacion cliente asigna empresa si el perfil tiene empresa; al endurecer perfil, el caso sin empresa deberia desaparecer. |
| `Incident` | `incidents.views.create_incident()`; `timeclock.services.ensure_missing_clock_incident()`; `dashboard.views.index()` para missing clock-in; `IncidentAdmin`; tests y backfill previo. | Las rutas intentan derivar empresa desde empleado, fichaje o turno; revisar automatismos antes de `null=False`. |
| `MonthlyHoursSummary` | `payroll.services.calculate_employee_summary()` y `recalculate_month()`; `MonthlyHoursSummaryAdmin`; tests y backfill previo. | Deriva empresa desde argumento `company` o desde `employee.company`; aceptar `company=None` es riesgo controlable tras endurecer empleados. |
| `PayrollDraft` | `payroll.services.generate_payroll_draft()`; `reports.views.payroll_csv()`; `PayrollDraftAdmin`; tests y backfill previo. | Reports pasa empresa del admin con empresa; el servicio todavia permite llamadas con `company=None`. |
| `PayrollDraftLine` | `payroll.services.generate_payroll_draft()`; `PayrollDraftLineInline`; tests y backfill previo. | Deriva empresa por fallback; depende de que summaries y drafts ya tengan empresa obligatoria. |

## Tests Existentes Que Cubren Creacion Con Company

| Modelo | Tests relevantes |
| --- | --- |
| `EmployeeProfile` | `test_admin_creates_user_and_employee_in_one_form`, `test_admin_create_employee_assigns_company_and_primary_workplace`, tests de aislamiento por empresa en `employees/tests.py`. |
| `Shift` | `test_admin_create_shift_saves_employee_company_and_workplace`, `test_duplicate_shift_saves_employee_company_and_workplace`, `test_copy_previous_week_saves_employee_company_and_workplace`, tests de filtrado por empresa en `scheduling/tests.py`. |
| `TimeClockEntry` | `test_valid_clock_saves_company_and_employee_primary_workplace`, `test_valid_clock_prefers_related_shift_workplace`, `test_admin_manual_clock_saves_company_and_workplace`, tests de historial/correccion por empresa en `timeclock/tests.py`. |
| `LeaveRequest` | `test_worker_create_request_saves_company`, tests de revision/listado por empresa en `leaves/tests.py`. |
| `Incident` | `test_worker_create_incident_saves_company`, `test_missing_clock_incident_saves_company_from_entry`, `test_missing_clock_incident_falls_back_to_employee_company`, tests de resolucion/listado por empresa en `incidents/tests.py` y `timeclock/tests.py`. |
| `MonthlyHoursSummary` | `test_recalculate_month_filters_by_company_when_provided`, `test_calculates_planned_and_clocked_hours`, `test_calculate_employee_summary_filters_by_company_data` en `payroll/tests.py`. |
| `PayrollDraft` | `test_generate_payroll_draft_filters_by_company`, `test_generate_payroll_draft_filters_out_employees_without_company`, reports CSV por empresa en `reports/tests.py`. |
| `PayrollDraftLine` | `test_generate_payroll_draft_filters_by_company`, `test_backfill_assigns_company_to_summary_draft_and_lines` en `payroll/tests.py`. |

## Tests Legacy Que Todavia Permiten Company Vacio

Estos tests existen porque las fases anteriores mantenian compatibilidad temporal con `company=NULL`. Deben eliminarse o reescribirse en las fases de hardening correspondientes.

| Area | Tests a revisar antes de `null=False` |
| --- | --- |
| `EmployeeProfile` | `test_profile_allows_empty_company_and_workplace_temporarily`; tests que crean perfiles legacy sin empresa para selectors, backfills o permisos de admin sin empresa. |
| `Shift` | `test_shift_allows_empty_company_and_workplace_temporarily`; tests de backfill y selectors que crean turnos sin empresa. |
| `TimeClockEntry` | `test_entry_allows_empty_company_and_workplace_temporarily`; tests de backfill, selectors y formulario sin empresa. |
| `LeaveRequest` | `test_request_allows_empty_company_temporarily`; tests de backfill, selectors, trabajador legacy y listados sin perfil. |
| `Incident` | `test_incident_allows_empty_company_temporarily`; tests de backfill desde empleado/turno/fichaje y listados legacy. |
| `MonthlyHoursSummary` | Tests de backfill y selectors que crean summaries sin empresa. |
| `PayrollDraft` | `test_backfill_assigns_company_to_summary_draft_and_lines` crea draft sin empresa; el servicio acepta `company=None`. |
| `PayrollDraftLine` | Tests de backfill crean lineas sin empresa; depende de `PayrollDraft` y summary/employee. |

## Riesgo De Django Admin

- `EmployeeProfileAdmin` no incluye `company` ni `primary_workplace` en `fieldsets`; con `company null=False` no podria crear perfiles validos sin ajuste previo o simultaneo.
- `ShiftAdmin` no incluye `company` ni `workplace`; `save_model()` solo rellena `created_by` y `modified_by`.
- `TimeClockEntryAdmin`, `LeaveRequestAdmin`, `IncidentAdmin` y admin de payroll usan formularios genericos o inlines sin autoasignacion de empresa.
- El hardening debe decidir si Django admin queda fuera de creacion operativa, si expone `company`, o si deriva empresa de relaciones antes de guardar.
- No se ha modificado Django admin en esta fase.

## Orden Recomendado De Hardening

1. `EmployeeProfile.company`
2. `Shift.company`
3. `LeaveRequest.company`
4. `Incident.company`
5. `TimeClockEntry.company`
6. `MonthlyHoursSummary.company`
7. `PayrollDraft.company`
8. `PayrollDraftLine.company`

## Propuesta De Primera Fase Ejecutable

Fase recomendada: `fase-hardening-employeeprofile-company-not-null`.

Alcance propuesto:

- Endurecer solo `EmployeeProfile.company`.
- No tocar `EmployeeProfile.primary_workplace` en esta fase.
- Revisar y ajustar Django admin para que no pueda crear perfiles sin empresa o para que exponga/asigne empresa de forma controlada.
- Reescribir tests temporales que permiten `EmployeeProfile.company=NULL`.
- Mantener la semantica de admin sin empresa cerrada en paneles operativos.
- Crear una unica migracion de modelo para este campo en esa fase, despues de aprobar el plan.
- Ejecutar tests completos antes de cerrar la fase.

## Condiciones Antes De Ejecutar Hardening

- No tocar `workplace` ni `primary_workplace` salvo plan especifico aprobado.
- No hacer hardening masivo.
- Aplicar una migracion por fase o por grupo minimo claramente justificado.
- Revisar rutas de creacion y Django admin antes de cambiar `null=False`.
- Eliminar o reescribir tests temporales de `company` nullable en el modelo que se endurezca.
- Ejecutar `./.venv/bin/python manage.py test` completo en cada fase ejecutable.
- Ejecutar `./.venv/bin/python manage.py check`.
- Ejecutar `./.venv/bin/python manage.py makemigrations --check --dry-run` despues de generar la migracion esperada.
- Ejecutar `git diff --check`.
- No tocar `BusinessConfig`, QR/IP por centro, templates ni diseno visual.

## Fuera De Alcance De Esta Fase

- Cambiar `null=True` a `null=False`.
- Crear migraciones.
- Hacer backfill.
- Tocar `workplace` o `primary_workplace`.
- Cambiar logica funcional.
- Cambiar Django admin.
- Tocar `BusinessConfig` o QR/IP por centro.
- Cambiar templates o diseno visual.
