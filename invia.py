#!/usr/bin/env python3
"""Fase 3: invio. Legge `sintesi.md`, manda la mail, aggiorna lo stato.

Lo stato viene aggiornato solo dopo che la mail e' partita davvero: se l'invio
fallisce, le voci restano candidate e la settimana dopo si ripresentano.

Variabili d'ambiente:
    GMAIL_USER            indirizzo Gmail che fa da mittente
    GMAIL_APP_PASSWORD    app password (non la password dell'account)
    MAIL_DESTINATARIO     destinatario (se manca, la mail va al mittente)

Uso:
    python invia.py [--prova]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import smtplib
import ssl
import sys
from datetime import datetime, timezone
from email.message import EmailMessage

import markdown

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465

# Come si presenta la mail: nome del mittente e apertura dell'oggetto.
NOME = "News Settimanali"

MESI = [
    "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
]

STILE = """
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
       font-size: 16px; line-height: 1.55; color: #1a1a1a; max-width: 640px;
       margin: 0 auto; padding: 24px 18px; }
h2 { font-size: 15px; text-transform: uppercase; letter-spacing: .08em; color: #666;
     border-bottom: 1px solid #e5e5e5; padding-bottom: 6px; margin: 32px 0 4px; }
h2:first-child { margin-top: 0; }
h3 { font-size: 17px; margin: 22px 0 2px; font-weight: 600; }
h3 a { color: #0b57d0; text-decoration: none; }
p { margin: 2px 0 0; color: #333; }
em { color: #777; }
.piede { margin-top: 40px; padding-top: 12px; border-top: 1px solid #e5e5e5;
         font-size: 13px; color: #999; }
.piede a { color: #999; }
"""


def data_italiana(quando: datetime) -> str:
    return f"{quando.day} {MESI[quando.month - 1]} {quando.year}"


def pulisci_sintesi(testo: str) -> str:
    """Toglie l'eventuale blocco di codice con cui il modello incarta l'output."""
    testo = testo.strip()
    if testo.startswith("```"):
        righe = testo.splitlines()
        righe = righe[1:]
        if righe and righe[-1].strip().startswith("```"):
            righe = righe[:-1]
        testo = "\n".join(righe).strip()
    return testo


def conta_voci(testo: str) -> int:
    return len(re.findall(r"^### ", testo, flags=re.MULTILINE))


def oggetto(testo: str, quando: datetime) -> str:
    voci = conta_voci(testo)
    if voci == 0:
        return f"{NOME}, {data_italiana(quando)} — niente di rilevante"
    return f"{NOME}, {data_italiana(quando)} — {voci} {'voce' if voci == 1 else 'voci'}"


def costruisci_html(testo: str, quando: datetime, repo_url: str | None) -> str:
    corpo = markdown.markdown(testo, extensions=["extra", "sane_lists"])
    piede = f"Generata il {data_italiana(quando)} dalla raccolta automatica."
    if repo_url:
        piede += f' <a href="{repo_url}">Fonti e archivio</a>.'
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{STILE}</style></head><body>"
        f"{corpo}<div class='piede'>{piede}</div>"
        "</body></html>"
    )


def normalizza(url: str) -> str:
    return url.strip().rstrip("/").lower()


def segna_inviati(stato: dict, candidati: list[dict], sintesi: str, quando: datetime) -> list[str]:
    """Segna come inviate solo le voci il cui link compare davvero nella
    sintesi. Quelle raccolte e non scelte restano candidate per il futuro."""
    testo = normalizza(sintesi)
    segnate = []
    for voce in candidati:
        url = normalizza(voce["url"])
        if url and url in testo:
            stato.setdefault("inviati", {})[voce["chiave"]] = {
                "data": quando.strftime("%Y-%m-%d"),
                "titolo": voce["titolo"],
                "url": voce["url"],
            }
            segnate.append(voce["chiave"])
    return segnate


def manda(oggetto_mail: str, testo: str, html: str, mittente: str, destinatario: str, password: str) -> None:
    messaggio = EmailMessage()
    messaggio["Subject"] = oggetto_mail
    messaggio["From"] = f"{NOME} <{mittente}>"
    messaggio["To"] = destinatario
    messaggio.set_content(testo)
    messaggio.add_alternative(html, subtype="html")

    contesto = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=contesto, timeout=60) as server:
        server.login(mittente, password)
        server.send_message(messaggio)


def main() -> int:
    parser = argparse.ArgumentParser(description="Invio della sintesi settimanale")
    parser.add_argument("--sintesi", default="sintesi.md")
    parser.add_argument("--stato", default="stato.json")
    parser.add_argument("--candidati", default="candidati.json")
    parser.add_argument("--prova", action="store_true", help="stampa la mail invece di mandarla, non tocca lo stato")
    argomenti = parser.parse_args()

    if not os.path.exists(argomenti.sintesi):
        print(f"invia.py: manca {argomenti.sintesi}", file=sys.stderr)
        return 1
    with open(argomenti.sintesi, encoding="utf-8") as f:
        sintesi = pulisci_sintesi(f.read())
    if not sintesi:
        print("invia.py: la sintesi e' vuota", file=sys.stderr)
        return 1

    quando = datetime.now(timezone.utc)
    repo = os.environ.get("GITHUB_REPOSITORY")
    html = costruisci_html(sintesi, quando, f"https://github.com/{repo}" if repo else None)
    titolo = oggetto(sintesi, quando)

    if argomenti.prova:
        print(f"--- Oggetto: {titolo}\n")
        print(sintesi)
        print(f"\n--- {conta_voci(sintesi)} voci. Prova: niente mail, stato non toccato.")
        return 0

    mittente = os.environ.get("GMAIL_USER", "").strip()
    # Google mostra l'app password a gruppi di quattro: se viene incollata con
    # gli spazi dentro, va tolti tutti, non solo quelli ai bordi.
    password = re.sub(r"\s+", "", os.environ.get("GMAIL_APP_PASSWORD", ""))
    destinatario = os.environ.get("MAIL_DESTINATARIO", "").strip() or mittente
    if not mittente or not password:
        print("invia.py: servono GMAIL_USER e GMAIL_APP_PASSWORD", file=sys.stderr)
        return 1

    manda(titolo, sintesi, html, mittente, destinatario, password)
    print(f"mail inviata a {destinatario}: {titolo}")

    with open(argomenti.stato, encoding="utf-8") as f:
        stato = json.load(f)
    candidati = []
    if os.path.exists(argomenti.candidati):
        with open(argomenti.candidati, encoding="utf-8") as f:
            candidati = json.load(f)

    segnate = segna_inviati(stato, candidati, sintesi, quando)
    stato["ultimo_invio"] = quando.isoformat(timespec="seconds")
    with open(argomenti.stato, "w", encoding="utf-8") as f:
        json.dump(stato, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")

    print(f"segnate come inviate {len(segnate)} voci su {len(candidati)} candidate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
