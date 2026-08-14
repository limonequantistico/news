#!/usr/bin/env bash
# Fase 2: sintesi. Interfaccia stupida: file in, file out.
#
# L'unica cosa che cambia tra un abbonamento e l'altro e' la riga del case
# qui sotto. Ne' la raccolta ne' l'invio sanno quale dei due sta girando.
#
#   SUMMARIZER=claude ./sintetizza.sh
#   SUMMARIZER=codex  ./sintetizza.sh
set -euo pipefail

SUMMARIZER="${SUMMARIZER:-claude}"
PROMPT="${1:-prompt.md}"
MATERIALE="${2:-materiale.md}"
SINTESI="${3:-sintesi.md}"

for file in "$PROMPT" "$MATERIALE"; do
  [ -s "$file" ] || { echo "sintetizza.sh: manca o e' vuoto: $file" >&2; exit 1; }
done

case "$SUMMARIZER" in
  claude) cat "$PROMPT" "$MATERIALE" | claude -p  > "$SINTESI" ;;
  codex)  cat "$PROMPT" "$MATERIALE" | codex exec > "$SINTESI" ;;
  *) echo "sintetizza.sh: SUMMARIZER sconosciuto: $SUMMARIZER" >&2; exit 1 ;;
esac

# Una sintesi vuota e' un guasto, non un "questa settimana niente": quello il
# sintetizzatore lo scrive a parole. Fallire qui fa arrivare la mail di GitHub.
[ -s "$SINTESI" ] || { echo "sintetizza.sh: $SUMMARIZER ha prodotto un file vuoto" >&2; exit 1; }

echo "sintesi scritta in $SINTESI ($(wc -c < "$SINTESI" | tr -d ' ') byte, summarizer: $SUMMARIZER)"
