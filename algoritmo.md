# Come vengono scelte le voci

Questo file risponde a una domanda sola: **perche' nella mail c'e' quella repo
e non un'altra?** Il `README` racconta come girano i pezzi, qui c'e' il criterio
di selezione. Quando lo dimenticherai, parti da qui.

La selezione e' fatta da due imbuti in fila, che fanno due lavori diversi:

1. **La raccolta** (`raccogli.py`, codice normale) decide **cosa puo' essere
   visto**. E' deterministica: dati gli stessi giorni e le stesse fonti, produce
   lo stesso elenco. Nessun giudizio.
2. **La sintesi** (`prompt.md` + il sintetizzatore) decide **cosa vale la pena
   mostrarti**. E' tutto giudizio, ma puo' scegliere solo dentro l'elenco che
   riceve.

La divisione non e' estetica: e' l'unico modo di sapere che il sistema ha
davvero guardato tutte le fonti, invece di scrivere una sintesi verosimile
pescando da quello che gia' sa.

---

## Imbuto 1 — cosa entra nel materiale

### Repo GitHub

Tre ricerche sulla Search API ufficiale (niente scraping della pagina trending,
che si rompe a ogni redesign), tutte ordinate per stelle decrescenti, 50
risultati ciascuna. Attenzione a come si legge `created:>data`: vuol dire
**creata dopo quella data**, cioe' "nata negli ultimi N giorni", non "vecchia
almeno N giorni".

| Etichetta | Query | Cosa cerca |
| --- | --- | --- |
| `della settimana` | `created:>7 giorni fa stars:>25` | le nate nell'ultima settimana, che corrono solo tra loro |
| `nuove` | `created:>30 giorni fa stars:>25` | repo dell'ultimo mese che hanno gia' raccolto attenzione |
| `in crescita` | `created:>1 anno fa pushed:>7 giorni fa stars:>500` | repo giovani, gia' affermate e ancora attive |

Le tre liste vengono unite e deduplicate per `owner/nome`, e chi compare in piu'
ricerche tiene l'etichetta della prima: in pratica ~135 repo a giro.

**Perche' la finestra a sette giorni non e' un doppione di quella a trenta.**
Ogni ricerca torna solo le prime 50 per stelle **assolute**, quindi il filtro
`stars:>25` e' quasi decorativo: la soglia d'ingresso vera e' "stare nei primi
50". Su trenta giorni quella soglia e' finita a 1.862 stelle, e una repo di tre
giorni non ci arriva mai, perche' compete con repo che hanno avuto dieci volte
il tempo di accumulare. Facendo correre le nate nell'ultima settimana solo tra
loro la soglia scende a ~344 stelle. Misurato sul giro del 14 agosto: senza
questa passata le repo dell'ultima settimana erano 7 su 50; con la passata sono
51 su 135.

**La crescita.** Per ogni repo vista, la raccolta salva in `stato.json` lo
snapshot delle stelle di oggi. Alla volta successiva confronta con lo snapshot
piu' recente di almeno due giorni prima e ne ricava un delta, riportando i
**giorni reali** trascorsi invece di dare per scontato che siano sette. E' il
surrogato di trending costruito in casa: non esiste un'API ufficiale della
pagina trending, quindi il segnale ce lo produciamo confrontando due fotografie.

La prima volta che una repo compare non c'e' storico, e nel materiale viene
scritto `crescita non nota: prima volta che la vediamo`.

**L'ordine conta.** Le repo arrivano al sintetizzatore ordinate per crescita, e
solo a parita' di crescita per stelle assolute. Chi non ha storico viene trattato
come crescita `-1`, quindi finisce sotto a chiunque abbia un delta noto non
negativo. Il sintetizzatore legge comunque tutta la lista: l'ordine e' un
suggerimento, non un taglio.

### Notizie

| Fonte | Come entra | Tetto |
| --- | --- | --- |
| Hacker News | API di ricerca ufficiale, storie degli ultimi 7 giorni **sopra i 150 punti**, ordinate per punti | 25 |
| TechCrunch | feed RSS, articoli degli ultimi 7 giorni | 25 |
| The Verge | feed RSS, articoli degli ultimi 7 giorni | 25 |

Differenza importante: **Hacker News si filtra da solo**, perche' la soglia dei
punti e' un giudizio collettivo gia' avvenuto. Dai feed RSS invece entra tutto
quello che e' recente, senza alcun filtro di rilevanza: li' lo scarto lo fa
interamente il sintetizzatore.

### Il filtro che non discute

Prima di scrivere `materiale.md`, la raccolta toglie **tutto cio' che ti e' gia'
stato mandato in passato**, leggendo `inviati` da `stato.json`. Il sintetizzatore
non lo vede proprio: non deve ricordarsi niente, non puo' riproporlo per sbaglio.

Lo storico delle stelle viene aggiornato anche per le repo gia' inviate — servono
a misurare la crescita, non a essere riproposte.

---

## Imbuto 2 — cosa arriva nella mail

Il sintetizzatore riceve `prompt.md` seguito da `materiale.md` e **nient'altro**:
niente web, niente memoria, nessuno strumento. Puo' solo scegliere e riassumere
quello che ha davanti, e ogni URL che scrive deve essere copiato alla lettera dal
materiale. E' il motivo per cui i link sono verificabili e non inventati.

Il criterio, testuale nel prompt, non e' "e' interessante" ma:

> **se salta questa riga, si perde qualcosa di utile?**

Con una lista esplicita di cosa buttare: raccolte fondi, gossip aziendale,
classifiche, polemiche, opinioni, roba di consumo; e per le repo le liste di
link, gli "awesome", i cloni e i corsi. La regola di chiusura e' **nel dubbio
scarta**.

I vincoli rigidi:

- massimo **10 voci** in tutto, massimo **5 per sezione**;
- **"questa settimana niente" e' una risposta legittima**, per una sezione o per
  entrambe — se il sistema fosse obbligato a riempire gli slot li riempirebbe di
  robaccia;
- ogni voce ha il link originale, una o due righe di spiegazione, niente hype.

Sulla crescita delle stelle il prompt dice una cosa precisa: e' un indizio di
attenzione, non di qualita'. Serve ad accorgersi di una repo, non a giustificarla.

---

## Cosa viene segnato come "gia' inviato"

`invia.py` non segna i candidati: segna **solo le voci il cui link compare
davvero nel testo della sintesi**. Quindi:

- una voce scelta non tornera' mai piu';
- una voce raccolta e scartata resta candidata e puo' uscire piu' avanti, se la
  settimana dopo regge il confronto.

E succede solo dopo che la mail e' partita davvero: se l'invio fallisce, lo stato
non si muove e la settimana dopo si ripresentano.

---

## Punti ciechi noti

Non sono bug, sono conseguenze delle scelte fatte. Vale la pena riconoscerli
prima di concludere che "il sistema non ha visto una cosa importante".

- **Giudica dalla descrizione, non dal codice.** Di una repo il sintetizzatore
  vede nome, descrizione, topics, linguaggio, stelle e crescita. Non apre il
  README. Per questo il link e' obbligatorio: il giudizio e' un filtro, la
  verifica resta tua.
- **Una repo vecchia che esplode oggi e' invisibile.** L'universo osservato e'
  "creata nell'ultimo anno". Un progetto del 2019 che diventa improvvisamente
  centrale non lo pesca nessuna delle due query.
- **Sotto le poche centinaia di stelle non si entra comunque.** Anche con la
  passata settimanale il taglio e' "primi 50 per stelle", quindi una repo nata
  ieri con 40 stelle resta fuori, per quanto buona sia. Il sistema vede cio' che
  ha gia' raccolto un minimo di attenzione, non cio' che la merita.
- **La finestra delle notizie e' rigida a 7 giorni, quella delle repo no.** Se un
  lunedi' il giro salta, le notizie di quella settimana sono perse per sempre; le
  repo invece si ripresentano al giro dopo.
- **Nessuna copertura fuori dal mondo tech**, per scelta.
- **Se una fonte cade**, il giro continua e il buco viene scritto in cima a
  `materiale.md` — quindi il quadro di quella settimana e' parziale e il
  sintetizzatore lo sa. Se cadono tutte, il giro fallisce apposta.

---

## Le manopole

Tutto quello che decide la selezione sta in due file, in cima:

| Cosa cambiare | Dove |
| --- | --- |
| testate RSS (aggiungere/togliere una riga) | `FEED_RSS` in `raccogli.py` |
| soglia dei punti di Hacker News | `HN_PUNTI_MINIMI` (150) |
| le due query GitHub | `RICERCHE_GITHUB` |
| ampiezza della finestra | `GIORNI_FINESTRA` (7) |
| quanti candidati per fonte | `MAX_REPO_PER_RICERCA` (50), `MAX_NOTIZIE_PER_FONTE` (25) |
| distanza minima tra due snapshot per calcolare la crescita | `GIORNI_MINIMI_CONFRONTO` (2) |
| **il criterio, i tetti, il tono** | `prompt.md` |

I tetti di 10 voci e 5 per sezione stanno nel prompt, non nel codice: sono un
giudizio, non un limite tecnico.

---

## Come si verifica a posteriori

Ogni giro archivia in `archivio/AAAA-MM-GG/` sia `materiale.md` (tutto quello che
ha visto) sia `sintesi.md` (quello che ha scelto). Il confronto tra i due dice
esattamente cosa e' stato scartato, e `stato.json` dice perche' certe cose non
sono nemmeno state considerate.

**Esempio reale, giro del 2026-08-14.** 99 repo + 55 notizie candidate → 10 voci
inviate, esattamente 5 + 5: entrambi i tetti raggiunti. Quattro notizie su cinque
venivano da Hacker News.

Quel "5 + 5" e' il numero da tenere d'occhio nel tempo: se ogni settimana la mail
arriva col massimo di voci, a tagliare e' il tetto e non il criterio, e il tetto
va abbassato. Se invece compaiono settimane da 6 o 7 voci, vuol dire che il
criterio morde da solo. L'archivio in git tiene il conto senza che tu debba
ricordartelo.
