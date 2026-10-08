# Despliegue en máquina propia

Probado: sintaxis de los scripts y `systemd-analyze verify` de las unidades. **No probado en un host real**
(la instalación, `sudo -u` del atajo y la publicación en Instagram): haz el primer ciclo con `DRY_RUN=true`.

## Requisitos
Linux con systemd, `python3` (con `venv`), `flock` (util-linux), salida a internet y, si no usas API key,
la CLI `claude` instalada. Máquina encendida a las horas de los timers (un VPS pequeño basta).

Hosts de salida necesarios: `api.anthropic.com` (o el login de `claude`), `api.bfl.ai` y `*.bfl.ai`,
`api.cloudinary.com`, `res.cloudinary.com`, `graph.facebook.com`.

## Instalación
```bash
git clone <repo> && cd instagram-agents-cafe-relojes
sudo deploy/install.sh                   # APP_DIR=/opt/instagram-swarm SVC_USER=swarm por defecto
sudo -u swarm -H claude login            # solo si no usas ANTHROPIC_API_KEY
sudoedit /etc/instagram-swarm.env        # secretos; deja DRY_RUN=true al principio
swarm run                                # primer ciclo a mano
```

## Qué corre y cuándo
| Unidad | Horario | Qué hace |
|---|---|---|
| `swarm-run.timer` | 07:30 diario (+0–20 min aleatorios) | Genera un post si hay < 3 en espera y publica lo aprobado |
| `swarm-publish.timer` | cada 30 min | Publica los aprobados cuya hora (`--at`) ya llegó |

`Persistent=true`: si la máquina estuvo apagada, el ciclo se ejecuta al volver. `flock` impide que dos ciclos
corran a la vez, y un post pasa a `publishing` antes de llamar a Instagram para no duplicarlo si el proceso muere.

## Operación diaria
```bash
swarm review                                  # posts pendientes: texto, imágenes y notas del revisor
swarm approve 3 --at 2026-10-10T14:00:00+00:00   # programar (UTC); sin --at sale en el próximo tick
swarm reject 3
swarm list ; swarm show 3
systemctl list-timers 'swarm-*'
journalctl -u swarm-run -u swarm-publish -f
```
Un post en `publishing` tras un fallo debe comprobarse a mano en Instagram antes de reintentarlo.

## Pasar a producción
1. Valida varios ciclos en `DRY_RUN=true` y revisa cada imagen y cifra técnica antes de aprobar.
2. Rellena `IG_USER_ID` / `IG_ACCESS_TOKEN` y cambia `DRY_RUN=false` en `/etc/instagram-swarm.env`.
3. Mantén `REQUIRE_APPROVAL=true` hasta que confíes en el enjambre, y `MAX_POSTS_PER_DAY` bajo.
4. El token de Instagram caduca (~60 días con tokens de larga duración): pon un recordatorio de renovación.
5. Copias de seguridad: `data/queue.db` es la cola y el historial.

## Alternativa: cron
`sudo -u swarm crontab deploy/crontab.example` (mismos horarios, log en `data/swarm.log`).

## Desinstalar
```bash
sudo systemctl disable --now swarm-run.timer swarm-publish.timer
sudo rm /etc/systemd/system/swarm-* /usr/local/bin/swarm /etc/instagram-swarm.env && sudo systemctl daemon-reload
```
