#!/bin/bash
# Rode na raiz do app no cPanel depois de puxar o GitHub.
# Atualiza banco, CSS/JS e recarrega o Passenger.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

APP_NAME="$(basename "$ROOT")"
for candidate in \
  "$HOME/virtualenv/$APP_NAME/3.12/bin/activate" \
  "$HOME/virtualenv/$APP_NAME/3.11/bin/activate" \
  "$HOME/virtualenv/$APP_NAME/3.10/bin/activate" \
  "$HOME/virtualenv/edu.innomove.com.br/3.12/bin/activate" \
  "$HOME/virtualenv/edu.innomove.com.br/3.11/bin/activate" \
  "$HOME/virtualenv/edu.innomove.com.br/3.10/bin/activate"
do
  if [ -f "$candidate" ]; then
    # shellcheck disable=SC1090
    source "$candidate"
    break
  fi
done

python manage.py migrate --noinput
python manage.py collectstatic --noinput
mkdir -p tmp
touch tmp/restart.txt
echo "Mitaka Edu publicado: static atualizado e Passenger recarregado."
