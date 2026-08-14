# Settimanale

Una mail, il lunedi' mattina, con al massimo dieci voci: le repo GitHub che si
stanno muovendo e le notizie tech che contano. Serve a non sentirsi indietro
senza seguire i social. Non e' un aggregatore, non e' un feed, non e' una
dashboard: e' una finestra settimanale, decisa da me invece che dal flusso.

Il vincolo che tiene in piedi il progetto non e' tecnico: **massimo dieci voci,
e "questa settimana niente" e' un output legittimo.** Un'email puntuale con
venti link diventa in tre settimane una mail che archivio senza aprire.

## Come funziona

Tre pezzi separati, tre file di scambio. Nessun pezzo sa cosa fanno gli altri.

```
raccogli.py   →  materiale.md   (codice normale, zero AI)
sintetizza.sh →  sintesi.md     (prompt.md + materiale.md → il sintetizzatore)
invia.py      →  la mail        (e aggiorna stato.json)
```

La raccolta resta codice deterministico perche' e' l'unico modo di sapere che
ha davvero guardato tutte le fonti, invece di scrivere una sintesi verosimile
pescando da quello che gia' sa. Nella v0 il sintetizzatore non naviga il web:
legge il materiale e basta.

### Fonti

- **GitHub**, Search API ufficiale (niente scraping della pagina trending, che
  si rompe a ogni redesign): repo nate negli ultimi 30 giorni ordinate per
  stelle, piu' repo dell'ultimo anno ancora attive. La **crescita settimanale**
  si ricava confrontando le stelle con lo snapshot salvato in `stato.json` la
  settimana prima — dal secondo giro in poi e' il vero delta.
- **Hacker News**, API di ricerca ufficiale: storie della settimana sopra i 150
  punti.
- **RSS**: TechCrunch, The Verge. Per togliere una testata, cancella la sua
  riga in `FEED_RSS` dentro `raccogli.py`.

### Stato

`stato.json` sta in git e lo committa il job stesso:

- `inviati` — cosa e' gia' uscito in mail, cosi' la settimana dopo non si
  ripresenta. Solo le voci il cui link compare davvero nella sintesi.
- `stelle` — storico degli snapshot, serve a calcolare la crescita.

Le voci raccolte e **non** scelte non finiscono in `inviati`: restano
candidate e possono uscire piu' avanti. Ogni giro archivia sia il materiale
grezzo sia la sintesi in `archivio/AAAA-MM-GG/`, quindi si puo' sempre vedere
cosa ha visto e cosa ha scartato.

## Setup

### 1. Secrets del repo

`Settings → Secrets and variables → Actions → New repository secret`:

| Secret | Cos'e' |
| --- | --- |
| `CLAUDE_CODE_OAUTH_TOKEN` | output di `claude setup-token` (serve un abbonamento Claude; il token viene stampato e non salvato) |
| `GMAIL_USER` | l'indirizzo Gmail che manda la mail |
| `GMAIL_APP_PASSWORD` | app password Google, **non** la password dell'account |
| `MAIL_DESTINATARIO` | dove arriva la mail (se manca, arriva al mittente) |

`GITHUB_TOKEN` non va creato: lo fornisce Actions da solo.

### 2. App password Gmail

Serve la verifica in due passaggi attiva sull'account. Poi
[myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords),
crei una password per "Settimanale" e incolli le 16 lettere nel secret (gli
spazi non contano). Mittente e destinatario sono entrambi tuoi, quindi la mail
non passa da nessun servizio esterno e non finisce in spam.

### 3. Prima prova

`Actions → Sintesi settimanale → Run workflow`. Lasciando `invia` a `true` la
mail arriva davvero; mettendolo a `false` il giro si ferma prima dell'invio e
trovi `materiale.md` e `sintesi.md` tra gli artifact della run.

## Cambiare sintetizzatore

Alterno gli abbonamenti Claude e Codex, quindi il passo di sintesi e' isolato
dietro un'interfaccia stupida: file in, file out. `prompt.md` e' lo stesso per
entrambi. In `sintetizza.sh`:

```sh
claude) cat "$PROMPT" "$MATERIALE" | claude -p  > "$SINTESI" ;;
codex)  cat "$PROMPT" "$MATERIALE" | codex exec > "$SINTESI" ;;
```

Per passare a Codex: cambi `SUMMARIZER: claude` in `SUMMARIZER: codex` nel
workflow e sistemi l'autenticazione. **La strada Codex e' piu' fragile e va
verificata quando ci si passa sopra**: non c'e' un comando pensato per la CI
come `setup-token`, le credenziali da abbonamento si rinnovano scrivendo su
disco, e in CI il disco sparisce a ogni run — quindi il refresh token nei
secrets invecchia e va rimesso a mano.

## Girare in locale

```sh
pip install -r requirements.txt
python raccogli.py            # scrive materiale.md
./sintetizza.sh               # scrive sintesi.md
python invia.py --prova       # stampa la mail invece di mandarla
```

`--prova` non manda niente e non tocca `stato.json`.

## Quando si rompe

Non serve che non si rompa mai, serve saperlo. Se il workflow va in errore
GitHub manda una mail — **all'utente che ha modificato per ultimo la sintassi
cron nel file**, quindi tieni quella riga tua. Casi previsti: token Claude
scaduto, app password revocata, fonte irraggiungibile (se una sola fonte cade
il giro continua e il buco e' scritto in cima a `materiale.md`; se cadono
tutte, il giro fallisce apposta).

Nota sui workflow schedulati: nei repo **pubblici** GitHub li disattiva dopo
60 giorni senza attivita', e conta solo un commit nuovo sul branch di default
(non issue, non tag). Il commit settimanale dell'archivio basta a tenerlo vivo:
per questo viene scritto anche nelle settimane senza niente da segnalare.
