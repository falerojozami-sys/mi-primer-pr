# Monitor de convocatorias JND

Te manda un mail cuando aparece una convocatoria nueva en
https://www.gub.uy/junta-nacional-drogas/comunicacion/convocatorias

## Cómo funciona

- Cada 3 horas, GitHub Actions corre `jnd_monitor.py`.
- El script lee las dos primeras páginas del listado y se queda con el slug (la parte final del enlace) de cada convocatoria.
- Si hay un slug que no estaba en `seen.json`, te avisa por mail y lo guarda.
- La primera corrida solo guarda lo que ya existe y no manda nada.
- Si la página cambia de estructura y el script no encuentra ninguna convocatoria, la corrida falla a propósito. GitHub te avisa por mail de la falla, así no te quedás sin monitoreo sin enterarte.

## Puesta en marcha

1. Creá un repositorio **privado** en GitHub y subí esta carpeta tal cual.
2. En Gmail, activá la verificación en dos pasos y generá una **contraseña de aplicación** (Cuenta de Google > Seguridad > Contraseñas de aplicaciones).
3. En el repo: Settings > Secrets and variables > Actions > New repository secret. Cargá estos cuatro:
   - `SMTP_HOST`: `smtp.gmail.com`
   - `SMTP_USER`: tu casilla de Gmail
   - `SMTP_PASS`: la contraseña de aplicación
   - `MAIL_TO`: donde querés recibir el aviso
4. En la pestaña Actions, corré el workflow a mano una vez (Run workflow). Esa primera corrida siembra `seen.json`.
5. Listo. De ahí en adelante corre solo.

## Probarlo localmente

```bash
pip install -r requirements.txt
python jnd_monitor.py
```

Sin las variables SMTP, imprime el aviso por consola en vez de mandarlo.

Para forzar un aviso de prueba, borrá una entrada de `seen.json` y volvé a correr el script.

## Ajustes comunes

- **Frecuencia:** cambiá la línea `cron` en `.github/workflows/monitor.yml`.
- **Avisar también cuando se reabre o se cierra una:** el estado de cada convocatoria ya se guarda en `seen.json`, solo falta comparar `status` antes de actualizarlo.
- **Telegram en vez de mail:** se reemplaza la función `notify()`.
