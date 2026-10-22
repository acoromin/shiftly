# Auditoria company/workplace NULL

Documento histórico archivado. Describe exclusivamente la base auditada en la fecha indicada; sus referencias a datos «actuales» corresponden a esa fecha. No acredita el estado de la base local de hoy ni establece tareas pendientes. La única hoja de ruta vigente es [plan-desarrollo.md](../plan-desarrollo.md).

Fecha: 2026-06-27

Fase: `fase-auditoria-company-null`

Ultimo commit base: `de4ee82` (`fase-forms-admin-empresa`)

## Resumen Ejecutivo

- Auditoria solo lectura realizada con ORM de Django sobre los modelos multiempresa principales.
- No se han hecho backfills.
- No se han creado migraciones.
- No se ha cambiado logica de negocio.
- No se han tocado templates.
- No se han bloqueado flujos ni endurecido campos.
- Datos auditados actuales: 6 registros en total.
- Registros con `company=NULL`: 0.
- Registros con `workplace=NULL` o `primary_workplace=NULL` en modelos con centro: 0.
- Registros potencialmente recuperables por backfill: 0.
- Inconsistencias detectadas: 0.

## Alcance Auditado

- `employees.EmployeeProfile.company`.
- `employees.EmployeeProfile.primary_workplace`.
- `scheduling.Shift.company`.
- `scheduling.Shift.workplace`.
- `timeclock.TimeClockEntry.company`.
- `timeclock.TimeClockEntry.workplace`.
- `leaves.LeaveRequest.company`.
- `incidents.Incident.company`.
- `payroll.MonthlyHoursSummary.company`.
- `payroll.PayrollDraft.company`.
- `payroll.PayrollDraftLine.company`.

## Fuera De Alcance

- `companies.Workplace.company`, porque debe ser obligatorio.
- `companies.JobPosition.company`, porque debe ser obligatorio.
- `incidents.Incident.shift`, porque es una relacion opcional.
- `incidents.Incident.timeclock_entry`, porque es una relacion opcional.
- `timeclock.TimeClockEntry.related_shift`, porque es una relacion opcional.

## Tabla Por Modelo

| Modelo | Total | company_null | workplace_null | backfillable | safe_backfillable | inconsistencias |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `EmployeeProfile` | 1 | 0 | 0 | 0 | 0 | 0 |
| `Shift` | 0 | 0 | 0 | 0 | 0 | 0 |
| `TimeClockEntry` | 2 | 0 | 0 | 0 | 0 | 0 |
| `LeaveRequest` | 0 | 0 | - | 0 | 0 | 0 |
| `Incident` | 0 | 0 | - | 0 | 0 | 0 |
| `MonthlyHoursSummary` | 1 | 0 | - | 0 | 0 | 0 |
| `PayrollDraft` | 1 | 0 | - | 0 | 0 | 0 |
| `PayrollDraftLine` | 1 | 0 | - | 0 | 0 | 0 |
| **Total** | **6** | **0** | **0** | **0** | **0** | **0** |

## Detalle Por Estado

| Modelo | Estado | Total | company_null | workplace_null |
| --- | --- | ---: | ---: | ---: |
| `EmployeeProfile` | `is_active=True` | 1 | 0 | 0 |
| `Shift` | activo/cancelado | 0 | 0 | 0 |
| `TimeClockEntry` | `manual` | 1 | 0 | 0 |
| `TimeClockEntry` | `valid` | 1 | 0 | 0 |
| `LeaveRequest` | todos los estados | 0 | 0 | - |
| `Incident` | todos los estados | 0 | 0 | - |
| `PayrollDraft` | `draft` | 1 | 0 | - |

## Backfill Potencial Revisado

Se revisaron registros con `company=NULL` recuperables desde relaciones existentes:

- `Shift.company=NULL` con `shift.employee.company` existente.
- `TimeClockEntry.company=NULL` con `entry.employee.company` existente.
- `TimeClockEntry.company=NULL` con `entry.related_shift.company` existente.
- `LeaveRequest.company=NULL` con `request.employee.company` existente.
- `Incident.company=NULL` con `incident.employee.company` existente.
- `Incident.company=NULL` con `incident.shift.company` existente.
- `Incident.company=NULL` con `incident.timeclock_entry.company` existente.
- `MonthlyHoursSummary.company=NULL` con `summary.employee.company` existente.
- `PayrollDraftLine.company=NULL` con `line.employee.company` o `line.draft.company` existente.
- `PayrollDraft.company=NULL` con todas sus lineas en la misma empresa.

Resultado: 0 registros backfillables porque no hay registros auditados con `company=NULL`.

## Inconsistencias Revisadas

Se revisaron, como minimo, estas inconsistencias:

- Registros con `workplace` informado pero `company=NULL`.
- Registros donde `workplace.company != company`.
- Registros donde `employee.company != record.company` cuando ambos existen.
- `PayrollDraftLine.company != PayrollDraft.company` cuando ambos existen.
- Fichajes donde `related_shift.company != entry.company` cuando ambos existen.
- Incidencias donde `shift.company != incident.company` cuando ambos existen.
- Incidencias donde `timeclock_entry.company != incident.company` cuando ambos existen.

Resultado: 0 inconsistencias detectadas.

## Registros Seguros De Backfill

- 0 registros.
- No hay backfill necesario con los datos actuales.

## Registros Que Requieren Decision Manual

- 0 registros.
- No se han detectado fuentes contradictorias de empresa para registros con `company=NULL`.
- No se han detectado registros con `company=NULL` sin fuente de recuperacion.

## Registros Que Bloquean Endurecer company A NOT NULL

- 0 registros por datos actuales.
- La auditoria no detecta bloqueos de datos para `company NOT NULL` en los modelos revisados.
- Antes de endurecer campos conviene decidir si se cierra el modo global temporal para administradores sin empresa.

## Registros Que Bloquean Endurecer workplace A NOT NULL

- 0 registros por datos actuales en modelos con `workplace` o `primary_workplace` auditados.
- La decision funcional de si todos los modelos deben exigir centro sigue pendiente.

Las recomendaciones de ejecución de esta auditoría se han retirado por estar superadas. Su versión original se conserva en el historial de Git.
