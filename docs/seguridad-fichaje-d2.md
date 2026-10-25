# Seguridad del fichaje y transición de QR (D2)

Estado: implementación y pruebas locales de D2, 2026-10-25. **Validación a través de un proxy de staging pendiente**. La etapa seguirá abierta hasta probar un entorno real con sus reglas de red. El orden vigente está en [plan-desarrollo.md](plan-desarrollo.md).

## Contrato de red

`get_client_ip` utiliza `REMOTE_ADDR`. Solo interpreta `X-Forwarded-For` cuando `REMOTE_ADDR` pertenece a una red configurada explícitamente en `TRUSTED_PROXY_CIDRS`. Recorre la cadena desde el proxy más cercano y toma el último salto no confiable. Si la cadena tiene IP inválidas, fragmentos vacíos, más de 20 saltos o contiene exclusivamente proxies confiables, la IP detectada es desconocida y el fichaje se bloquea. Las cabeceras recibidas desde una conexión directa se ignoran. La configuración rechaza redes que confíen en todas las direcciones (`0.0.0.0/0`, `::/0`).

En desarrollo, sin proxy, dejar `TRUSTED_PROXY_CIDRS` vacío. En un despliegue con Nginx único delante de Django y conexión al proceso por loopback:

```text
TRUSTED_PROXY_CIDRS=127.0.0.1/32,::1/128
```

```nginx
location / {
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_pass http://127.0.0.1:8000;
}
```

La aplicación debe aceptar conexiones **solo del proxy** mediante bind local, firewall o red privada. El proxy de entrada debe reemplazar las cabeceras de IP recibidas del cliente, como en el ejemplo, o reconstruir una cadena documentada de proxies confiables. No usar `$proxy_add_x_forwarded_for` en el primer proxy si conserva una cabecera enviada por Internet sin filtrarla. Cuando haya varios proxies, declarar solo sus rangos efectivos, verificar cómo forman `X-Forwarded-For` y probar peticiones desde cada ruta. El comportamiento de selección del último salto no confiable coincide con la descripción de [`real_ip_recursive` de Nginx](https://nginx.org/en/docs/http/ngx_http_realip_module.html). [OWASP documenta el riesgo de suplantar IP mediante cabeceras HTTP](https://community.owasp.org/pages/attacks/ip_spoofing_via_http_headers.html).

La IP permitida en cada centro es la dirección pública de salida que **ve esta aplicación** cuando el móvil está conectado a su WiFi. Si cambia, el técnico debe comprobar la nueva salida desde la red del local, actualizar `Workplace.public_wifi_ip` y probar un fichaje válido y otro desde fuera. Un centro solo admite una IP por ahora; sedes con salidas IPv4 e IPv6 distintas requieren ampliar el modelo antes de prometer cobertura de ambas. La IP compartida del WiFi y el QR son controles de contexto, no una prueba suficiente de presencia física de una persona.

## QR por centro

Los QR nuevos se generan en **Administración técnica → Centros de trabajo → Generar QR** o con `setup_xarlot_clock`. La URL tiene formato `/fichar/#workplace=<UUID>&token=<secreto>`. [El fragmento tras `#` no se envía en la petición GET](https://developer.mozilla.org/en-US/docs/Web/URI/Reference/Fragment): el navegador lo recoge, lo retira de la barra y envía la credencial por POST al confirmar. Si el trabajador no está autenticado, la pantalla de acceso conserva el fragmento en el campo POST `next` y vuelve al fichaje después del login. El centro se busca por identificador público, empresa del empleado y estado activo; se verifica un único hash de secreto. Si hay turno activo asociado a un centro, ambos centros deben coincidir.

El secreto aparece una vez en la página técnica de generación, enviada con `Cache-Control: no-store`, o en la salida del comando. No se guarda en mensajes/cookies del Admin. Guardar esa URL en una herramienta de impresión de QR controlada por la organización; no enviarla a servicios públicos de creación de QR, analítica, capturas compartidas ni incidencias con registro de URLs. Probar el QR impreso desde un móvil autenticado y sin autenticar antes de colocarlo. Evitar registrar cuerpos POST y cabeceras `Location` con secretos en proxy, servidor y herramientas de observabilidad. La URL nueva no pone el secreto en la query de acceso, pero no sustituye esas prácticas de registro.

**Rotación:** generar un nuevo QR, imprimirlo, retirar el anterior y comprobar que el antiguo ya no permite fichar; la generación reemplaza el hash anterior. **Revocación inmediata:** usar la acción **Revocar QR** del mismo Admin o desactivar el centro. Para restablecer el servicio, generar e imprimir otro QR. Una IP alterada no cambia el secreto del QR; actualizar la IP y probar los controles por separado.

## Transición de QR anteriores

Los QR ya impresos con `/fichar/?token=...` siguen admitidos inicialmente (`CLOCK_ALLOW_LEGACY_QR=1`). Esta compatibilidad todavía puede leer el secreto en logs de URL y verificar hashes de todos los centros activos de la empresa cuando no hay turno con centro. Es una transición temporal: inventariar QR impresos, regenerar e instalar los nuevos, verificar cada centro y configurar `CLOCK_ALLOW_LEGACY_QR=0` en todos los procesos. Con ese valor, solo se aceptan QR con identificador público. Los QR antiguos permanecen rechazados después del cambio y se deben retirar físicamente.

## Límites de intentos

Se cuentan intentos de login de aplicación y Admin técnico durante ventanas de cinco minutos: máximo 10 por combinación IP/usuario y 60 por IP. El fichaje admite 20 intentos por empleado y minuto; el exceso se rechaza antes de verificar hashes de QR. Los contadores se guardan en la base de datos mediante claves hash, sin nombre ni IP en claro en esa tabla. Programar diariamente `./.venv/bin/python manage.py prune_security_throttles` para borrar contadores de más de un día. En un despliegue con varios procesos, todos deben utilizar la misma base. Estos límites no sustituyen medidas de borde ante ataques volumétricos; su eficacia concurrente debe medirse en PostgreSQL (D4–D5).

## Verificación restante para cerrar D2

- Preparar y documentar un staging con proxy, reglas de red, hosts y HTTPS. Desde una conexión directa a la aplicación, verificar que no es accesible desde Internet.
- Probar con móvil en WiFi autorizado, desde fuera, con `X-Forwarded-For` falsificada y a través de cada proxy real. Comprobar la IP detectada y que el QR antiguo puede retirarse sin bloquear usuarios pendientes.
- Inspeccionar los logs HTTP y de errores para confirmar que los secretos de QR nuevos no aparecen en URL, cuerpo registrado, redirecciones registradas o trazas. Ejecutar prueba de login sin sesión y rotación/revocación con QR impreso.

Las pruebas automatizadas locales cubren la política de IP, los casos de empresa/centro/turno, el flujo HTTP sin secreto en query, la migración de IDs y los límites de intentos. Sus resultados y el estado real figuran en [estado-sesion.md](estado-sesion.md).
