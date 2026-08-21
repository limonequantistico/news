#!/usr/bin/env python3
"""Fase 1: raccolta deterministica. Zero AI.

Interroga le fonti con codice normale e scrive `materiale.md`, che e' l'unico
input fattuale del sintetizzatore. Scrive anche `candidati.json` (usato da
invia.py per capire quali voci sono finite nella mail) e aggiorna lo storico
delle stelle in `stato.json`, che e' cio' che permette di calcolare la crescita
settimanale delle repo senza dipendere dalla pagina trending.

Uso:
    python raccogli.py [--stato stato.json] [--out materiale.md]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import feedparser

# --------------------------------------------------------------------------
# Fonti. Per togliere una testata cancella la sua riga.
#
# Terzo campo: pezzi di URL da buttare via prima di guardare la data. Serve solo
# ai feed che non sono elenchi di articoli. AI Hero pubblica un unico rss.xml
# che e' l'indice di tutto il sito, quindi accanto ai post ci finiscono le
# landing dei workshop, le pagine di iscrizione e le voci del dizionario: sono
# pagine sempre uguali, non notizie, e la data di pubblicazione non le
# distingue. Per le testate normali la tupla e' vuota e non filtriamo niente.
# --------------------------------------------------------------------------

FEED_RSS = [
    ("TechCrunch", "https://techcrunch.com/feed/", ()),
    ("The Verge", "https://www.theverge.com/rss/index.xml", ()),
    (
        "AI Hero",
        "https://www.aihero.dev/rss.xml",
        ("/workshops/", "/newsletter", "/subscribe", "/ai-coding-dictionary/"),
    ),
]

# Hacker News: front page della settimana via API ufficiale di ricerca.
HN_PUNTI_MINIMI = 150

# Ricerche GitHub, in ordine di freschezza: chi compare in piu' ricerche tiene
# l'etichetta della prima.
#
# La finestra a sette giorni non e' un doppione di quella a trenta. Ogni ricerca
# torna solo le prime cinquanta per stelle assolute, quindi in una finestra di
# trenta giorni una repo di tre giorni compete con repo che hanno avuto dieci
# volte il tempo di accumulare stelle e non entra mai: la soglia d'ingresso
# reale finisce sopra il migliaio. Facendo correre le nate nell'ultima settimana
# solo tra loro, la soglia scende a poche centinaia e le repo appena uscite
# hanno una possibilita'.
RICERCHE_GITHUB = [
    ("della settimana", "created:>{sette_giorni_fa} stars:>25"),
    ("nuove", "created:>{trenta_giorni_fa} stars:>25"),
    ("in crescita", "created:>{un_anno_fa} pushed:>{sette_giorni_fa} stars:>500"),
]

GIORNI_FINESTRA = 7
MAX_REPO_PER_RICERCA = 50
MAX_NOTIZIE_PER_FONTE = 25

# Distanza minima tra due snapshot perche' il confronto voglia dire qualcosa
# (evita di misurare la "crescita" tra due lanci a mano dello stesso giorno).
GIORNI_MINIMI_CONFRONTO = 2

# Quanto teniamo lo storico prima di potarlo.
MAX_SNAPSHOT_PER_REPO = 10
GIORNI_OBLIO_REPO = 120
GIORNI_OBLIO_INVIATI = 400

USER_AGENT = "news-settimanale/1.0 (+https://github.com)"

# --------------------------------------------------------------------------
# Utilita'
# --------------------------------------------------------------------------


def ora() -> datetime:
    return datetime.now(timezone.utc)


def giorno(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def scarica(url: str, headers: dict[str, str] | None = None, tentativi: int = 3) -> bytes:
    """GET con qualche tentativo. Le fonti ogni tanto danno 5xx o vanno in timeout."""
    intestazioni = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    intestazioni.update(headers or {})
    ultimo_errore: Exception | None = None
    for tentativo in range(tentativi):
        try:
            richiesta = Request(url, headers=intestazioni)
            with urlopen(richiesta, timeout=30) as risposta:
                return risposta.read()
        except (HTTPError, URLError, TimeoutError, OSError) as errore:
            ultimo_errore = errore
            if tentativo < tentativi - 1:
                time.sleep(2 * (tentativo + 1))
    raise RuntimeError(f"{url}: {ultimo_errore}")


def scarica_json(url: str, headers: dict[str, str] | None = None):
    return json.loads(scarica(url, headers).decode("utf-8"))


def ripulisci(testo: str | None, limite: int = 400) -> str:
    """Toglie tag HTML e spazi di troppo dai sommari RSS."""
    if not testo:
        return ""
    senza_tag = re.sub(r"<[^>]+>", " ", testo)
    normalizzato = re.sub(r"\s+", " ", unescape(senza_tag)).strip()
    if len(normalizzato) > limite:
        normalizzato = normalizzato[: limite - 1].rstrip() + "…"
    return normalizzato


def numero(n: int) -> str:
    return f"{n:,}".replace(",", ".")


# --------------------------------------------------------------------------
# Stato
# --------------------------------------------------------------------------


def stato_vuoto() -> dict:
    return {"ultimo_run": None, "inviati": {}, "stelle": {}}


def carica_stato(percorso: str) -> dict:
    if not os.path.exists(percorso):
        return stato_vuoto()
    with open(percorso, encoding="utf-8") as f:
        stato = json.load(f)
    for chiave, default in stato_vuoto().items():
        stato.setdefault(chiave, default)
    return stato


def salva_stato(percorso: str, stato: dict) -> None:
    with open(percorso, "w", encoding="utf-8") as f:
        json.dump(stato, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def registra_stelle(
    stato: dict, nome_repo: str, stelle: int, adesso: datetime
) -> tuple[int, int] | None:
    """Salva lo snapshot di oggi e restituisce (crescita, giorni) rispetto al
    piu' recente snapshot abbastanza vecchio da essere un confronto sensato.
    None se non c'e' ancora storico: e' il caso della prima settimana.

    Il confronto riporta i giorni veri invece di dare per scontato che siano
    sette: se un giro salta o viene lanciato a mano, il numero resta onesto."""
    storico = stato["stelle"].setdefault(nome_repo, [])
    oggi = giorno(adesso)
    limite = giorno(adesso - timedelta(days=GIORNI_MINIMI_CONFRONTO))

    crescita = None
    confrontabili = [voce for voce in storico if voce[0] <= limite]
    if confrontabili:
        data_base, stelle_base = confrontabili[-1]
        giorni = (adesso.date() - datetime.strptime(data_base, "%Y-%m-%d").date()).days
        crescita = (stelle - stelle_base, giorni)

    storico = [voce for voce in storico if voce[0] != oggi]
    storico.append([oggi, stelle])
    stato["stelle"][nome_repo] = storico[-MAX_SNAPSHOT_PER_REPO:]
    return crescita


def pota_stato(stato: dict, adesso: datetime) -> None:
    limite_repo = giorno(adesso - timedelta(days=GIORNI_OBLIO_REPO))
    stato["stelle"] = {
        nome: storico
        for nome, storico in stato["stelle"].items()
        if storico and storico[-1][0] >= limite_repo
    }
    limite_inviati = giorno(adesso - timedelta(days=GIORNI_OBLIO_INVIATI))
    stato["inviati"] = {
        chiave: voce
        for chiave, voce in stato["inviati"].items()
        if voce.get("data", "9999")[:10] >= limite_inviati
    }


# --------------------------------------------------------------------------
# Fonti: GitHub
# --------------------------------------------------------------------------


def cerca_github(query: str, token: str | None) -> list[dict]:
    url = (
        "https://api.github.com/search/repositories"
        f"?q={quote(query)}&sort=stars&order=desc&per_page={MAX_REPO_PER_RICERCA}"
    )
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return scarica_json(url, headers).get("items", [])


def raccogli_repo(stato: dict, adesso: datetime, errori: list[str]) -> list[dict]:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("attenzione: nessun GITHUB_TOKEN, uso il rate limit anonimo", file=sys.stderr)

    sostituzioni = {
        "sette_giorni_fa": giorno(adesso - timedelta(days=7)),
        "trenta_giorni_fa": giorno(adesso - timedelta(days=30)),
        "un_anno_fa": giorno(adesso - timedelta(days=365)),
    }

    grezze: dict[str, dict] = {}
    for etichetta, modello in RICERCHE_GITHUB:
        query = modello.format(**sostituzioni)
        try:
            risultati = cerca_github(query, token)
        except RuntimeError as errore:
            errori.append(f"GitHub ({etichetta}): {errore}")
            continue
        for repo in risultati:
            nome = repo["full_name"]
            if nome not in grezze:
                repo["_ricerca"] = etichetta
                grezze[nome] = repo

    voci = []
    for nome, repo in grezze.items():
        stelle = repo.get("stargazers_count", 0)
        crescita = registra_stelle(stato, nome, stelle, adesso)
        voci.append(
            {
                "chiave": f"github:{nome}",
                "tipo": "repo",
                "titolo": nome,
                "url": repo.get("html_url", ""),
                "descrizione": (repo.get("description") or "").strip(),
                "stelle": stelle,
                "crescita": crescita[0] if crescita else None,
                "giorni_crescita": crescita[1] if crescita else None,
                "linguaggio": repo.get("language") or "—",
                "creata": (repo.get("created_at") or "")[:10],
                "topics": repo.get("topics") or [],
                "ricerca": repo["_ricerca"],
            }
        )

    # Prima la crescita vera, poi le stelle assolute: chi non ha storico non
    # viene penalizzato piu' di tanto, resta ordinato per dimensione.
    voci.sort(key=lambda v: (v["crescita"] if v["crescita"] is not None else -1, v["stelle"]), reverse=True)
    return voci


# --------------------------------------------------------------------------
# Fonti: notizie
# --------------------------------------------------------------------------


def raccogli_hacker_news(adesso: datetime, errori: list[str]) -> list[dict]:
    da = int((adesso - timedelta(days=GIORNI_FINESTRA)).timestamp())
    url = (
        "https://hn.algolia.com/api/v1/search?tags=story"
        f"&numericFilters=created_at_i>{da},points>{HN_PUNTI_MINIMI}"
        f"&hitsPerPage={MAX_NOTIZIE_PER_FONTE}"
    )
    try:
        dati = scarica_json(url)
    except RuntimeError as errore:
        errori.append(f"Hacker News: {errore}")
        return []

    voci = []
    for storia in dati.get("hits", []):
        discussione = f"https://news.ycombinator.com/item?id={storia['objectID']}"
        collegamento = storia.get("url") or discussione
        voci.append(
            {
                "chiave": f"hn:{storia['objectID']}",
                "tipo": "notizia",
                "titolo": storia.get("title") or "(senza titolo)",
                "url": collegamento,
                "discussione": discussione,
                "fonte": "Hacker News",
                "data": (storia.get("created_at") or "")[:10],
                "punti": storia.get("points") or 0,
                "commenti": storia.get("num_comments") or 0,
                "estratto": ripulisci(storia.get("story_text")),
            }
        )
    voci.sort(key=lambda v: v["punti"], reverse=True)
    return voci


def raccogli_feed(
    nome: str,
    url: str,
    adesso: datetime,
    errori: list[str],
    escludi: tuple[str, ...] = (),
) -> list[dict]:
    try:
        grezzo = scarica(url)
    except RuntimeError as errore:
        errori.append(f"{nome}: {errore}")
        return []

    feed = feedparser.parse(grezzo)
    limite = adesso - timedelta(days=GIORNI_FINESTRA)
    voci = []
    for articolo in feed.entries:
        pubblicato = articolo.get("published_parsed") or articolo.get("updated_parsed")
        if pubblicato:
            quando = datetime(*pubblicato[:6], tzinfo=timezone.utc)
            if quando < limite:
                continue
        else:
            quando = adesso
        collegamento = articolo.get("link") or ""
        if not collegamento:
            continue
        if any(pezzo in collegamento for pezzo in escludi):
            continue
        voci.append(
            {
                "chiave": f"rss:{articolo.get('id') or collegamento}",
                "tipo": "notizia",
                "titolo": ripulisci(articolo.get("title"), 200) or "(senza titolo)",
                "url": collegamento,
                "fonte": nome,
                "data": giorno(quando),
                "punti": None,
                "commenti": None,
                "estratto": ripulisci(articolo.get("summary")),
            }
        )
    return voci[:MAX_NOTIZIE_PER_FONTE]


# --------------------------------------------------------------------------
# Scrittura di materiale.md
# --------------------------------------------------------------------------


def scrivi_materiale(
    percorso: str,
    repo: list[dict],
    notizie: list[dict],
    scartate: int,
    errori: list[str],
    adesso: datetime,
) -> None:
    righe: list[str] = []
    righe.append(f"# Materiale grezzo — {giorno(adesso)}")
    righe.append("")
    righe.append(
        f"Finestra: dal {giorno(adesso - timedelta(days=GIORNI_FINESTRA))} al {giorno(adesso)}. "
        f"Candidati: {len(repo)} repo, {len(notizie)} notizie. "
        f"Voci gia' inviate in passato ed escluse a monte: {scartate}."
    )
    righe.append("")
    if errori:
        righe.append("**Fonti non raggiungibili in questo giro** (tienine conto: il quadro e' parziale):")
        for errore in errori:
            righe.append(f"- {errore}")
        righe.append("")

    righe.append(f"## Repo GitHub ({len(repo)})")
    righe.append("")
    if not repo:
        righe.append("_Nessun candidato._")
        righe.append("")
    for indice, voce in enumerate(repo, 1):
        if voce["crescita"] is None:
            crescita = " (crescita non nota: prima volta che la vediamo)"
        else:
            segno = "+" if voce["crescita"] >= 0 else "−"
            crescita = (
                f" ({segno}{numero(abs(voce['crescita']))} in {voce['giorni_crescita']} giorni)"
            )
        righe.append(f"### R{indice}. {voce['titolo']}")
        righe.append(f"- URL: {voce['url']}")
        righe.append(f"- Stelle: {numero(voce['stelle'])}{crescita}")
        righe.append(f"- Linguaggio: {voce['linguaggio']} · creata il {voce['creata']} · ricerca: {voce['ricerca']}")
        if voce["topics"]:
            righe.append(f"- Topics: {', '.join(voce['topics'][:10])}")
        righe.append(f"- Descrizione: {voce['descrizione'] or '(nessuna)'}")
        righe.append("")

    righe.append(f"## Notizie ({len(notizie)})")
    righe.append("")
    if not notizie:
        righe.append("_Nessun candidato._")
        righe.append("")
    for indice, voce in enumerate(notizie, 1):
        righe.append(f"### N{indice}. {voce['titolo']}")
        righe.append(f"- URL: {voce['url']}")
        meta = [voce["fonte"], voce["data"]]
        if voce.get("punti") is not None:
            meta.append(f"{voce['punti']} punti · {voce['commenti']} commenti")
        righe.append(f"- Fonte: {' · '.join(m for m in meta if m)}")
        if voce.get("discussione") and voce["discussione"] != voce["url"]:
            righe.append(f"- Discussione: {voce['discussione']}")
        if voce["estratto"]:
            righe.append(f"- Estratto: {voce['estratto']}")
        righe.append("")

    with open(percorso, "w", encoding="utf-8") as f:
        f.write("\n".join(righe))


# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Raccolta deterministica delle fonti")
    parser.add_argument("--stato", default="stato.json")
    parser.add_argument("--out", default="materiale.md")
    parser.add_argument("--candidati", default="candidati.json")
    argomenti = parser.parse_args()

    adesso = ora()
    stato = carica_stato(argomenti.stato)
    errori: list[str] = []

    repo = raccogli_repo(stato, adesso, errori)

    notizie = raccogli_hacker_news(adesso, errori)
    for nome, url, escludi in FEED_RSS:
        notizie.extend(raccogli_feed(nome, url, adesso, errori, escludi))

    # Lo storico delle stelle viene aggiornato per tutte le repo viste, anche
    # per quelle gia' inviate: serve a misurare la crescita, non a riproporle.
    gia_inviate = set(stato["inviati"])
    totale_prima = len(repo) + len(notizie)
    repo = [voce for voce in repo if voce["chiave"] not in gia_inviate]
    notizie = [voce for voce in notizie if voce["chiave"] not in gia_inviate]
    scartate = totale_prima - len(repo) - len(notizie)

    if not repo and not notizie:
        if errori:
            print("nessun candidato e tutte le fonti in errore:", file=sys.stderr)
            for errore in errori:
                print(f"  - {errore}", file=sys.stderr)
            return 1
        print("attenzione: nessun candidato nuovo questa settimana", file=sys.stderr)

    scrivi_materiale(argomenti.out, repo, notizie, scartate, errori, adesso)

    with open(argomenti.candidati, "w", encoding="utf-8") as f:
        json.dump(
            [
                {"chiave": v["chiave"], "tipo": v["tipo"], "titolo": v["titolo"], "url": v["url"]}
                for v in repo + notizie
            ],
            f,
            indent=2,
            ensure_ascii=False,
        )
        f.write("\n")

    stato["ultimo_run"] = adesso.isoformat(timespec="seconds")
    pota_stato(stato, adesso)
    salva_stato(argomenti.stato, stato)

    print(f"raccolti {len(repo)} repo e {len(notizie)} notizie ({scartate} gia' inviate, escluse)")
    for errore in errori:
        print(f"  fonte in errore: {errore}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
