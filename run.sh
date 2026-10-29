#!/usr/bin/env bash
set -euo pipefail

# Funziona anche se lo script viene chiamato da un'altra cartella.
cd "$(dirname "$0")"

python_bin=$(command -v python3)
if [[ -x python/.venv/bin/python ]]; then
    python_bin="$PWD/python/.venv/bin/python"
fi

porta_python=${NICKGAME_PY_PORT:-50010}
export NICKGAME_GO_PORT=${NICKGAME_GO_PORT:-50011}
export NICKGAME_GO_HTTP_URL="http://127.0.0.1:$NICKGAME_GO_PORT"
export NICKGAME_GO_WS_URL="ws://127.0.0.1:$NICKGAME_GO_PORT"

# Controlla le porte prima di avviare i server, senza fermare altri programmi.
"$python_bin" - "$porta_python" "$NICKGAME_GO_PORT" <<'PY'
import socket
import sys

if sys.argv[1] == sys.argv[2]:
    sys.exit('Flask e Go devono usare due porte diverse.')
for porta in sys.argv[1:]:
    try:
        with socket.socket() as connessione:
            # Come i server, consente il riavvio dopo connessioni in TIME_WAIT.
            # Un server ancora in ascolto continua invece a bloccare la porta.
            connessione.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            connessione.bind(('127.0.0.1', int(porta)))
    except (OSError, ValueError, OverflowError):
        sys.exit(f'Porta {porta} occupata o non valida. Ferma il vecchio server prima di riprovare.')
PY

# Compila il piccolo programma C++ chiamato da Flask per premi e acquisti.
mkdir -p cpp/build
g++ -std=c++17 -Wall -Wextra -Werror -O2 cpp/main.cpp cpp/economia.cpp -o cpp/build/nickgame-economia
# La rete usa soltanto la libreria standard C++ e i pesi già allenati.
g++ -std=c++17 -Wall -Wextra -Werror -O2 cpp/bot/main.cpp cpp/bot/rete_forza4.cpp -o cpp/build/nickgame-bot

# Prepara database e chiave, poi compila Go: eseguire il binario permette
# di fermare il server direttamente, senza lasciare figli di "go run" attivi.
(cd python && "$python_bin" -c 'import app')
(cd go && mkdir -p build && go build -o build/nickgame-sync .)

processi=()
ferma_server() {
    if (( ${#processi[@]} > 0 )); then
        kill "${processi[@]}" 2>/dev/null || true
        wait "${processi[@]}" 2>/dev/null || true
    fi
}
trap ferma_server EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

(cd go && exec ./build/nickgame-sync) &
processi+=("$!")
(cd python && exec "$python_bin" -m flask --app app run --host 127.0.0.1 --port "$porta_python" --no-reload) &
processi+=("$!")

echo "Nickgame: http://127.0.0.1:$porta_python — Ctrl+C ferma entrambi i server."

# Se uno dei due si arresta, chiudiamo anche l'altro.
wait -n "${processi[@]}"
