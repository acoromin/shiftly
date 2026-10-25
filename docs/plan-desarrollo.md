# Plan de desarrollo de Shiftly

Fecha: 2026-10-22. Estado: plan vigente; D1 completada localmente, D2 en curso, D3–D9 pendientes.

Este documento es la única hoja de ruta vigente y define prioridades, alcance y criterios de salida. [estado-sesion.md](estado-sesion.md) conserva el avance real, las verificaciones y la siguiente tarea. Los planes anteriores se han retirado; sus versiones originales permanecen en Git y los cierres de fases se conservan en la bitácora.

## Objetivo de producto

Ofrecer a pequeñas empresas de hostelería una gestión fiable de turnos, fichajes, incidencias y horas para gestoría. Hostelería es la hipótesis inicial, basada en la aplicación existente; debe validarse con los responsables del piloto antes de ampliar sectores.

El recorrido que debe funcionar de principio a fin es: alta de empresa y centro → incorporación de trabajadores → planificación → fichaje desde móvil → revisión de incidencias → aprobación de horas → exportación reproducible.

El éxito del primer lanzamiento se mide por la fiabilidad de ese recorrido y la autonomía del cliente. El número de modelos, pruebas o funcionalidades no acredita por sí solo que el producto esté preparado.

## Punto de partida comprobado (antes de D1)

- Código de referencia: `9985608`, fase 8, publicado en `origin/main`.
- Última regresión completa: 203 pruebas correctas sobre SQLite. No acredita concurrencia en PostgreSQL ni capacidad de producción.
- Empresa obligatoria en las entidades operativas; centros seleccionables y QR/IP por centro; Django Admin reservado a técnicos.
- Base local con una empresa y un centro, sin empleados ni actividad. La base original no se ha localizado.
- Configuración de desarrollo con SQLite y `DEBUG=True`. `check --deploy` produjo seis advertencias en el entorno local revisado.
- Riesgos observados: mantenimiento global editable por administradores de empresa; confianza incondicional en `X-Forwarded-For`; consultas que escriben resúmenes/incidencias; aprobaciones de horas extra reiniciadas por el recálculo; fichaje sin protección completa frente a solicitudes simultáneas.
- No se han acreditado un despliegue de producción, pruebas de carga, restauración externa ni validación con clientes.

## Decisiones de arquitectura

1. Mantener el monolito modular Django y las pantallas renderizadas en servidor. Organizar las operaciones de negocio en servicios explícitos; las vistas coordinan autorización, entrada y respuesta.
2. Usar PostgreSQL como base objetivo para staging, producción y pruebas de integración/concurrencia. SQLite puede seguir sirviendo para desarrollo rápido, pero no será la validación final del lanzamiento.
3. Mantener tablas compartidas con `company` explícita. Obtener la empresa autorizada de la sesión/permisos y aplicarla en consultas y escrituras; un identificador recibido del cliente no autoriza acceso. Cubrir también admin, exportaciones y tareas programadas.
4. Separar configuración de plataforma, empresa y centro. El mantenimiento global pertenece al operador técnico; los parámetros propios del negocio pertenecen a su empresa/centro.
5. Registrar las operaciones críticas y su auditoría en una misma transacción. Repetir una petición no debe repetir su efecto; las correcciones deben conservar el valor original y el autor.
6. Mantener las lecturas sin efectos de negocio. Recalcular, aprobar, cerrar y generar exportaciones serán acciones explícitas. Las tareas periódicas tendrán ejecución y reintentos independientes de que alguien abra una página.
7. Medir consultas, latencia y consumo antes de añadir cachés, colas o índices. Introducir trabajadores de fondo cuando lo requieran la programación fiable o las mediciones.
8. Conservar inicialmente una empresa por perfil. Si el piloto necesita gestores con varias empresas, diseñar membresías y selección de empresa antes de habilitar ese acceso.

## Orden de ejecución

**D1 está completada localmente; D2 sigue en curso y D3–D9 pendientes**. Cada una se divide en cambios pequeños que puedan revisarse y desplegarse. Una dependencia incompleta impide declarar cerrada la etapa dependiente.

| Etapa | Resultado | Dependencias | Condición para avanzar |
| --- | --- | --- | --- |
| D1 (cerrada localmente) | Separar permisos de plataforma y empresa | Fase 8 | Una empresa no altera la operación de otra |
| D2 (en curso) | Asegurar la identificación del centro y la IP | D1 | Cabeceras manipuladas y QR ajenos no autorizan fichajes |
| D3 | Corregir consultas y cálculo de horas | D1 | Consultar conserva aprobaciones y resultados históricos |
| D4 | PostgreSQL, entornos y validación automática | D1–D3 | CI y staging reproducibles con PostgreSQL |
| D5 | Fichajes y transiciones seguros ante concurrencia | D2–D4 | Reintentos y peticiones simultáneas conservan invariantes |
| D6 | Auditoría e histórico verificables | D3–D5 | Cambios críticos y cierres se pueden reconstruir |
| D7 | Recorrido de cliente y operación desde móvil | D1–D6 | El cliente completa sus tareas sin acceso técnico |
| D8 | Operación, restauración y capacidad medidas | D4–D7 | Evidencias de recuperación, carga y alertas |
| D9 | Piloto con empresas y decisión de lanzamiento | D1–D8 | Recorrido completo validado durante un ciclo mensual |

### D1 — Permisos y configuración global (cerrada localmente)

- Inventariar rutas, roles y configuraciones globales. Definir una matriz de permisos para técnico, administrador de empresa y trabajador, incluyendo cuentas/perfiles inactivos y sin empresa.
- Reservar el mantenimiento global al técnico. Separar nombre, tolerancias y otros ajustes del negocio cuando corresponda; revisar también enlaces y formularios visibles.
- Probar con dos empresas que los GET/POST no permiten consultar ni modificar configuración ajena, y que el administrador de una empresa no bloquea a los trabajadores de la otra.
- Cierre: matriz documentada, pruebas de autorización y ausencia de escrituras indebidas, regresión completa correcta. Auditar datos antes de cualquier migración de configuración.

**Resultado:** mantenimiento reservado al técnico; nombre y tolerancia por empresa; perfiles/empresas inactivos bloqueados en rutas cliente. [Matriz, inventario y migración](permisos-configuracion.md). Las verificaciones ejecutadas están en [estado-sesion.md](estado-sesion.md).

**D2 iniciada:** el fallo de `X-Forwarded-For` se reprodujo y se corrigió localmente. El avance, las verificaciones restantes y la guía operativa están en [seguridad-fichaje-d2.md](seguridad-fichaje-d2.md) y [estado-sesion.md](estado-sesion.md).

### D2 — Fichaje, red y credenciales de centro

Implementación y pruebas locales en curso. La comprobación integrada de proxy, QR impreso y logs en staging sigue pendiente; D2 permanece abierta.

- Definir el contrato de despliegue con proxy: origen permitido, cabeceras que se eliminan/reconstruyen y acceso directo a la aplicación. Usar la IP de conexión salvo que proceda de un proxy expresamente confiable.
- Añadir pruebas de `X-Forwarded-For` falsificado, cadenas de proxies, IP inválida, QR de otra empresa, centro inactivo y credenciales revocadas.
- Revisar la selección de centro de la fase 8: un QR debe permitir localizar un candidato autorizado sin comprobar hashes costosos de todos los centros. Considerar identificador público de centro más secreto aleatorio, con transición definida para QR antiguos.
- Definir rotación, impresión y revocación del QR, evitar tokens en logs y añadir protección contra intentos repetidos de login/fichaje.
- Cierre: comprobación integrada a través del proxy de staging, pruebas de aislamiento correctas y guía de configuración. Documentar los límites de QR/IP como evidencia de presencia y el procedimiento cuando cambia la IP del local.

### D3 — Consultas y cálculo de horas fiables

- Separar cálculo puro, persistencia del resumen y decisiones manuales. Abrir dashboard, horas o informes no debe crear incidencias, reiniciar aprobaciones ni regenerar borradores.
- Mantener las horas extra aprobadas y observaciones revisadas fuera de los valores sobrescritos por el cálculo. Una descarga debe recuperar una exportación identificada; la generación será explícita y repetible sin duplicados accidentales.
- Definir con ejemplos las reglas de jornada: descansos, turnos partidos/nocturnos, entradas sin salida, cambio de mes/año, vacaciones que abarcan varios meses, redondeo y cambios de contrato. Incluir empleados dados de baja que tuvieron actividad en el periodo.
- Corregir el emparejamiento de fichajes que cruzan límites de mes, contar solo los días del permiso dentro del periodo y distinguir número de incidencias de horas pendientes.
- Cierre: tabla de casos de negocio con resultados esperados, pruebas de límites temporales y preservación de aprobaciones; consultar y descargar no modifica el estado de negocio. Las reglas aún no validadas se identificarán como tales.

### D4 — Base de datos, entornos y CI

- Añadir configuración por entorno con secretos obligatorios en producción, `DEBUG=False`, hosts explícitos, HTTPS/cookies seguras, estáticos y servidor de aplicación de producción.
- Preparar PostgreSQL en desarrollo de integración, CI y staging. Auditar y ensayar la migración de datos con copia, conteos, relaciones y comparación de resultados; la base local vacía no sustituye la auditoría de una base recuperada.
- Ejecutar en cada cambio pruebas, comprobación de migraciones, validaciones Django y revisión de formato. CI debe probar las migraciones relevantes y bloquear una entrega fallida.
- Documentar arranque desde un checkout limpio, dependencias fijadas, revisión periódica de actualizaciones y procedimiento de despliegue/recuperación por versión.
- Cierre: suite completa en PostgreSQL, staging desplegado de forma reproducible, ensayo de migración y `check --deploy` sin advertencias sin resolver o justificar para ese entorno.

### D5 — Concurrencia y transiciones de negocio

- Definir explícitamente entrada, salida y corrección. Conservar coherencia entre la jornada abierta, el centro y el turno, incluyendo cambios de centro y fichajes cerca de los límites del turno.
- Procesar lectura de estado, validación, escritura y auditoría dentro de transacciones cortas. Usar bloqueo sobre una entidad estable del empleado/jornada cuando sea necesario y claves de idempotencia para reintentos.
- Revisar también creación simultánea de turnos solapados, generación de incidencias y revisión/cancelación de solicitudes. Las restricciones de base de datos deben reforzar las invariantes que puedan representarse allí.
- Probar carreras reales con conexiones independientes en PostgreSQL; una prueba secuencial de instancias obsoletas no demuestra exclusión concurrente.
- Cierre: doble envío, reintento y solicitudes paralelas generan un solo efecto válido, sin duplicados de incidencias ni estados incompatibles; fallo intermedio no deja escrituras parciales.

### D6 — Auditoría, correcciones y cierre mensual

- Incorporar la antigua fase 9: contexto de empresa/centro en `AuditLog`, distinguiendo eventos de plataforma y registros históricos cuyo contexto no se pueda demostrar.
- Registrar actor, fecha, acción, entidad, antes/después y motivo en las operaciones críticas. Proteger la auditoría frente a edición/borrado ordinarios y comprobar el aislamiento de sus lectores.
- Definir los estados del periodo: borrador, revisado y cerrado. Conservar una versión reproducible de lo exportado; una corrección posterior al cierre debe tener una operación explícita y trazable.
- Acordar política de conservación, acceso y eliminación de datos personales antes del piloto con datos reales; validar los requisitos aplicables con asesoramiento competente. La auditoría técnica por sí sola no acredita cumplimiento legal.
- Cierre: reconstrucción demostrada de una corrección y de un cierre/exportación, eventos críticos completos, transacciones atómicas y documentación coherente con el comportamiento real.

### D7 — Cliente autónomo y uso desde móvil

- Validar el segmento inicial y observar tareas reales con responsables de 1–2 negocios. Preparar primero datos ficticios representativos.
- Entregar alta guiada de empresa/centro, incorporación de trabajadores, recuperación de acceso, configuración/rotación del QR y prueba de conectividad con permisos de empresa.
- Mostrar centro y acción a confirmar antes del fichaje, confirmación inequívoca del resultado y recuperación comprensible frente a falta de red, sesión caducada o reintento.
- Completar planificación, solicitud/revisión, corrección justificada y exportación. Añadir búsqueda/paginación donde los límites actuales ocultan registros; comprobar móvil, teclado y mensajes de error.
- Cierre: un administrador y un trabajador completan el recorrido acordado sin usar Django Admin ni pedir cambios de base de datos. Registrar dificultades y tiempos observados; no dar por validada la experiencia solo con pruebas de servidor.

### D8 — Operación y capacidad

- Programar la detección de incidencias y otros trabajos periódicos fuera de las visitas al dashboard, con reintentos seguros y supervisión de fallos.
- Medir y reducir consultas por empleado en dashboard e informes. Evaluar índices compuestos por empresa/fecha/estado con planes de consulta y datos representativos.
- Definir registros estructurados, identificador de petición, métricas de latencia/errores y alertas para fallos de fichaje, tareas, copias y disponibilidad. Excluir secretos y minimizar datos personales.
- Automatizar copias cifradas fuera del servidor y ensayar restauración a un entorno separado, con validación de integridad. Documentar responsable y respuesta a incidentes.
- Ejecutar carga reproducible sobre PostgreSQL y el proxy real, anotando hardware, dataset, mezcla de solicitudes, resultados y coste estimado por empresa.
- Cierre: restauración y alertas demostradas, despliegue/recuperación ensayados y objetivos de capacidad evaluados. Si no se alcanzan, registrar el límite y corregirlo antes de ampliar el piloto.

Objetivos iniciales propuestos para D8, pendientes de contrastar con tamaño y coste del piloto:

| Medida | Objetivo de evaluación |
| --- | --- |
| Datos sintéticos | 100 empresas, 10.000 empleados y un año de fichajes |
| Carga | 50 usuarios concurrentes durante 15 minutos, incluyendo una ráfaga de fichajes; especificar tasa y mezcla exactas en el ensayo |
| Latencia del servidor | p95 menor de 1 s en lectura habitual y 2 s en fichaje |
| Errores | Menos del 0,1 % de errores técnicos y cero pérdidas/duplicados de operaciones confirmadas |
| Recuperación | RPO máximo propuesto de 1 hora y RTO de 4 horas, sujetos a infraestructura, coste y prueba |

Estos objetivos no son capacidad demostrada ni compromisos comerciales. Los cálculos/exportaciones extensos tendrán un presupuesto propio o ejecución de fondo; no se ocultarán dentro del promedio de páginas rápidas.

### D9 — Piloto y decisión de lanzamiento

- Operar con 1–2 empresas durante un ciclo mensual completo, con responsables y canal de soporte definidos.
- Medir fichajes correctos, correcciones necesarias, conciliación de horas, tiempo de planificación/cierre y solicitudes de ayuda. Comparar con el proceso previo del cliente.
- Hacer seguimiento de incidentes, uso semanal y voluntad de seguir usando/pagar el producto; documentar resultados, también los negativos.
- Cierre: ningún incidente crítico de aislamiento o pérdida de datos abierto, horas conciliadas y exportación validada por el responsable del negocio, recorrido utilizable y operación soportable. Decidir expansión, ajustes o ampliación del piloto con esa evidencia.
- Facturación recurrente, integraciones y nuevos sectores se priorizarán después según necesidades verificadas. Microservicios, aplicaciones nativas y otras ampliaciones requieren un problema concreto y mediciones que las justifiquen.

## Forma de trabajar y evidencia de cierre

- Antes de cada etapa: comprobar Git, leer la bitácora y auditar código/datos afectados. Registrar supuestos y decisiones que cambien reglas de negocio.
- Cuando haya cambios de datos: copia verificable, auditoría previa, protección de las rutas de escritura, migración ensayada y verificación posterior. Conservar históricos; no asignar empresas o centros por conveniencia.
- Para cambios funcionales: pruebas que reproduzcan el riesgo, regresión requerida y comprobación manual del recorrido afectado. En concurrencia, usar PostgreSQL y conexiones independientes.
- Para cambios exclusivamente documentales: revisar enlaces, coherencia y diff; no repetir la suite de aplicación sin motivo.
- Cerrar con código/documentación revisables, resultados y limitaciones anotados en la bitácora. Usar commits pequeños; integrar mediante cambios con CI cuando D4 esté disponible.
- Un objetivo no medido se mantiene pendiente. No fijar fechas de entrega de todo el plan antes de desglosar la siguiente etapa y conocer datos/entorno del piloto.

## Referencias técnicas

- [Lista de despliegue de Django 5.2](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/): configuración y comprobaciones de producción.
- [Bases de datos en Django 5.2](https://docs.djangoproject.com/en/5.2/ref/databases/): diferencias entre motores y límites de SQLite.
- [Transacciones](https://docs.djangoproject.com/en/5.2/topics/db/transactions/) y [select_for_update](https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update): atomicidad y bloqueo.
- [Política de seguridad de Django](https://docs.djangoproject.com/en/5.2/internals/security/): responsabilidad del servidor/proxy sobre cabeceras reenviadas.
