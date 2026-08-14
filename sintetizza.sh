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

# Un token copiato dal terminale porta con se' l'a capo con cui il terminale
# lo ha mandato a capo: incollato nel secret diventa una stringa su due righe
# e l'header di autorizzazione viene rifiutato.
if [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then
  CLAUDE_CODE_OAUTH_TOKEN="$(printf '%s' "$CLAUDE_CODE_OAUTH_TOKEN" | tr -d '[:space:]')"
  export CLAUDE_CODE_OAUTH_TOKEN
fi

# Il sintetizzatore scrive in un file di appoggio, non direttamente in
# "$SINTESI": i suoi errori escono su stdout, non su stderr, quindi scrivendo
# dritti sul file finale un guasto diventa invisibile nel log e resta sepolto
# nel file. Qui invece, se fallisce, quello che ha scritto va nel log.
GREZZO="$(mktemp)"
trap 'rm -f "$GREZZO"' EXIT
esito=0

case "$SUMMARIZER" in
  claude) cat "$PROMPT" "$MATERIALE" | claude -p  > "$GREZZO" || esito=$? ;;
  codex)  cat "$PROMPT" "$MATERIALE" | codex exec > "$GREZZO" || esito=$? ;;
  *) echo "sintetizza.sh: SUMMARIZER sconosciuto: $SUMMARIZER" >&2; exit 1 ;;
esac

if [ "$esito" -ne 0 ]; then
  echo "sintetizza.sh: $SUMMARIZER e' uscito con codice $esito e ha scritto:" >&2
  cat "$GREZZO" >&2
  exit "$esito"
fi

# Una sintesi vuota e' un guasto, non un "questa settimana niente": quello il
# sintetizzatore lo scrive a parole. Fallire qui fa arrivare la mail di GitHub.
[ -s "$GREZZO" ] || { echo "sintetizza.sh: $SUMMARIZER ha prodotto un file vuoto" >&2; exit 1; }

mv "$GREZZO" "$SINTESI"
trap - EXIT

echo "sintesi scritta in $SINTESI ($(wc -c < "$SINTESI" | tr -d ' ') byte, summarizer: $SUMMARIZER)"
