#!/usr/bin/env bash
# Instalación en una máquina Linux con systemd. Idempotente. Uso: sudo deploy/install.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/instagram-swarm}"
SVC_USER="${SVC_USER:-swarm}"
ENV_FILE="/etc/instagram-swarm.env"

[ "$(id -u)" -eq 0 ] || { echo "Ejecuta como root (sudo)." >&2; exit 1; }
command -v python3 >/dev/null || { echo "Falta python3." >&2; exit 1; }
command -v flock >/dev/null || { echo "Falta flock (paquete util-linux)." >&2; exit 1; }
SRC="$(cd "$(dirname "$0")/.." && pwd)"

id "$SVC_USER" >/dev/null 2>&1 || useradd --system --create-home --shell /bin/bash "$SVC_USER"

mkdir -p "$APP_DIR"
# copia el código sin tocar data/ (cola) ni secretos
tar -C "$SRC" --exclude=.git --exclude=data --exclude=.env --exclude=.venv --exclude=__pycache__ -cf - . | tar -C "$APP_DIR" -xf -
mkdir -p "$APP_DIR/data" "$APP_DIR/sources"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install -q --upgrade pip
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"
chown -R "$SVC_USER":"$SVC_USER" "$APP_DIR"

if [ ! -f "$ENV_FILE" ]; then
  cp "$APP_DIR/.env.example" "$ENV_FILE"
  CLAUDE_PATH="$(command -v claude || true)"
  {
    echo
    echo "# Añadido por install.sh"
    [ -n "$CLAUDE_PATH" ] && echo "CLAUDE_BIN=$CLAUDE_PATH" && echo "PATH=$(dirname "$CLAUDE_PATH"):/usr/local/bin:/usr/bin:/bin"
  } >> "$ENV_FILE"
  chown root:"$SVC_USER" "$ENV_FILE"
  chmod 640 "$ENV_FILE"
  echo "Creado $ENV_FILE (DRY_RUN=true y REQUIRE_APPROVAL=true por defecto)."
else
  echo "Conservo $ENV_FILE existente."
fi

for f in swarm-run.service swarm-run.timer swarm-publish.service swarm-publish.timer; do
  sed -e "s|@APP_DIR@|$APP_DIR|g" -e "s|@SVC_USER@|$SVC_USER|g" "$SRC/deploy/systemd/$f" > "/etc/systemd/system/$f"
done
sed -e "s|@APP_DIR@|$APP_DIR|g" -e "s|@SVC_USER@|$SVC_USER|g" "$SRC/deploy/swarm" > /usr/local/bin/swarm
chmod 755 /usr/local/bin/swarm
systemctl daemon-reload
systemctl enable --now swarm-run.timer swarm-publish.timer

cat <<MSG

Instalado en $APP_DIR (usuario: $SVC_USER). Pasos que faltan:
  1. Autenticar la CLI de Claude como ese usuario (si no usas ANTHROPIC_API_KEY):
       sudo -u $SVC_USER -H claude login
  2. Editar los secretos:  sudoedit $ENV_FILE
     (BFL_API_KEY, CLOUDINARY_*, IG_USER_ID, IG_ACCESS_TOKEN). Mantén DRY_RUN=true hasta validar.
  3. Probar un ciclo a mano:
       sudo -u $SVC_USER -H bash -c 'set -a; . $ENV_FILE; set +a; cd $APP_DIR && .venv/bin/python -m swarm.cli run'
  4. Revisar y aprobar:  swarm review / approve / reject  (ver deploy/README.md)
  5. Logs:  journalctl -u swarm-run -u swarm-publish -f    |    systemctl list-timers 'swarm-*'
MSG
