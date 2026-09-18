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
| AI Hero | feed RSS, voci degli ultimi 7 giorni, meno gli URL esclusi (vedi sotto) | 25 |

Differenza importante: **Hacker News si filtra da solo**, perche' la soglia dei
punti e' un giudizio collettivo gia' avvenuto. Dai feed RSS invece entra tutto
quello che e' recente, senza alcun filtro di rilevanza: li' lo scarto lo fa
interamente il sintetizzatore.

**Perche' AI Hero ha un filtro sugli URL e le altre no.** Le due testate
pubblicano un feed di articoli: ogni voce e' una notizia, e la data basta a dire
se e' di questa settimana. AI Hero (il blog di Matt Pocock: gli stessi contenuti
che manda per email, pubblici, quindi non serve iscriversi) espone invece un
solo `rss.xml` che e' l'indice dell'intero sito — 188 voci, di cui 70 sono le
pagine del suo "AI Coding Dictionary", piu' le landing dei workshop e le pagine
di iscrizione. Sono pagine permanenti, non uscite: la data non le distingue dai
post, perche' cambia quando la pagina viene ritoccata. Quindi la riga in
`FEED_RSS` porta un terzo campo con i pezzi di URL da buttare prima ancora di
guardare la data — `/workshops/`, `/newsletter`, `/subscribe`,
`/ai-coding-dictionary/` — e per le altre testate quel campo resta vuoto.

Resta codice, non giudizio: e' una lista fissa di prefissi, non una valutazione
del contenuto. Misurato il 21 agosto 2026, su trenta giorni il feed dava 5 voci
e il filtro ne toglieva 1 (la landing "AI Coding Crash Course"), lasciando i 4
post veri. Sulla finestra vera dei 7 giorni quella landing era **l'unica** voce
in finestra, quindi il primo giro con questa fonte porta zero voci in piu': la
cadenza di AI Hero e' circa un post a settimana, non e' una fonte che riempie.

### Paper

| Fonte | Come entra | Tetto |
| --- | --- | --- |
| Hugging Face Daily Papers | API ufficiale, una chiamata per ognuno dei 7 giorni, paper **sopra i 50 voti**, ordinati per voti | 25 |

**Perche' non arXiv.** Misurato sulla settimana 8–14 settembre 2026, arXiv ha
pubblicato 1.994 paper sulle sole cs.AI, cs.LG e cs.CL messe insieme (1.057 +
984 + 535, deduplicati), circa 285 al giorno. Buttarli nel materiale
significherebbe passare da ~150 candidati a ~2.150 e chiedere al sintetizzatore
di scegliere tra titoli e abstract senza alcun segnale: sceglierebbe i titoli
piu' promettenti, che e' esattamente il modo in cui questo sistema non deve
funzionare. Daily Papers e' invece una lista compilata da persone e votata: la
stessa struttura dei punti di Hacker News, cioe' un giudizio gia' avvenuto fuori
di qui.

Numeri della stessa settimana su Daily Papers: 133 paper segnalati in 7 giorni,
di cui 84 sopra i 10 voti, 47 sopra i 30, **27 sopra i 50** (la soglia scelta) e
15 sopra i 100. Cinquanta tiene i candidati nello stesso ordine di grandezza
delle altre fonti — venticinque voci circa — senza ridurli a una manciata.

**La data che conta e' quella della segnalazione**, non quella di pubblicazione
su arXiv. Un paper uscito il 7 settembre puo' comparire nella lista del 16: e'
il giorno in cui qualcuno se n'e' accorto, ed e' quello che ci interessa.
Filtrare per `publishedAt` lo avrebbe fatto sparire dalla finestra. Lo stesso
paper puo' comparire in piu' giorni: teniamo la prima segnalazione e il
conteggio voti piu' alto.

**Sabato e domenica la lista e' vuota.** Non e' un guasto ed e' irrilevante per
un giro del lunedi' che guarda indietro sette giorni. Un giorno non raggiungibile
per un errore vero finisce invece tra le fonti in errore in cima a `materiale.md`,
con l'elenco dei giorni persi.

**Il codice come tiebreak.** L'API restituisce anche la repo GitHub collegata al
paper, quando c'e' (13 su 25 in un giorno campione), con le stelle. Finisce nel
materiale come fatto, ed e' il criterio a parita' di tutto il resto nel prompt:
un paper con codice pubblico e' verificabile, uno senza va preso sulla parola.

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

- massimo **10 voci tra Repo e Notizie**, 5 per sezione, piu' **massimo 3
  paper** che stanno fuori da quel conto. I paper non tolgono posto a nessuno:
  e' una scelta, ed e' l'unico punto in cui la mail puo' superare le dieci voci
  (vedi *La prova dei paper* piu' sotto);
- **"questa settimana niente" e' una risposta legittima**, per una sezione o per
  entrambe — se il sistema fosse obbligato a riempire gli slot li riempirebbe di
  robaccia;
- ogni voce ha il link originale, una o due righe di spiegazione, niente hype.

Sulla crescita delle stelle il prompt dice una cosa precisa: e' un indizio di
attenzione, non di qualita'. Serve ad accorgersi di una repo, non a giustificarla.
Sui voti dei paper dice la stessa cosa, piu' forte: il sintetizzatore legge
**l'abstract**, che gli autori scrivono per farsi leggere, e il prompt gli chiede
esplicitamente di scartare l'annuncio di modello travestito da paper.

Che quel paragrafo morda si vede sui giri di prova del 18 settembre 2026: dei 24
candidati ha sempre scelto voci molto in basso nella lista — sessanta voti circa
— scartando tutti quelli sopra i 100, compresi i tre in cima con 681, 403 e 310
voti, che erano presentazioni di modelli con un numero di arXiv sopra.

**I paper non si segnalano, si spiegano.** E' la differenza vera tra quella
sezione e le altre due, ed e' nata da un errore del primo giro: le voci erano
corrette e illeggibili — "Grouped Value Attention: efficient KV caching" dice
qualcosa a chi segue la letteratura e niente a chi scrive software. Per repo e
notizie una riga basta perche' il lettore sa gia' cos'e' una repo e cos'e' un
rilascio; di un paper non conosce il gergo e non ha modo di capire dall'abstract
se lo riguarda, quindi un paper solo segnalato e' un paper che non aprira' mai.
Il prompt chiede percio' quattro o cinque righe: cosa hanno fatto, partendo dal
problema che c'era prima, e cosa cambierebbe per chi costruisce cose — con
l'obbligo di spiegare ogni termine tecnico nella frase stessa e il permesso
esplicito di concludere "per ora e' un risultato di laboratorio". E' l'unica
eccezione alla regola delle due righe, e vale solo li'.

Ha una conseguenza sulla selezione, scritta nel prompt: tra due paper si prende
quello la cui conseguenza si riesce a spiegare. Un risultato importante che non
si rende comprensibile in quattro righe, in questa mail, vale meno di uno piu'
piccolo che si capisce.

---

## La prova dei paper

La sezione paper e' accesa **in prova dal 18 settembre 2026**, e la prova ha una
data di scadenza: dopo quattro numeri — cioe' **dal 19 ottobre 2026** — si
guarda l'archivio e si decide, invece di lasciarla li' per inerzia.

Le domande a cui rispondere allora, in ordine:

1. Di quei paper, quanti ne hai aperti davvero?
2. Quante volte la spiegazione era comprensibile senza cercare altro fuori?
3. La mail e' diventata piu' lunga di quanto ti va di leggere il lunedi'?

La terza non e' secondaria. I paper stanno **fuori** dal tetto delle dieci voci,
quindi una settimana piena adesso puo' arrivare a tredici voci, e tre di quelle
sono lunghe quattro righe invece di una. E' esattamente il tipo di crescita che
il `README` dice di temere — "un'email puntuale con venti link diventa in tre
settimane una mail che archivio senza aprire" — e qui e' stata accettata di
proposito, per non far competere i paper con le altre sezioni prima di sapere se
valgono. Se dopo quattro numeri la risposta e' "bella ma non la leggo", la cosa
giusta e' togliere la sezione, non accorciarla.

Gli esiti possibili sono tre e vanno scritti qui quando si decide: **togliere**
(si cancella `raccogli_paper` e la sezione dal prompt, una ventina di righe),
**tenere ma dentro il tetto** (i paper tornano a competere con repo e notizie),
**tenere cosi'**.

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
- **Dei paper legge l'abstract, non il paper.** E' il punto cieco piu' grosso di
  questa fonte: un abstract lo scrivono gli autori per farsi leggere, e a
  differenza di una repo non c'e' nemmeno un numero di stelle che dica se
  qualcuno lo usa davvero. Il link e' l'unica difesa, come per le repo.
- **I paper che nessuno vota non esistono.** Sotto i 50 voti su Daily Papers non
  si entra, e su Daily Papers finisce solo cio' che qualcuno ha segnalato: un
  buon paper di un gruppo senza pubblico e' fuori dal campo visivo, e i ~1.970
  paper a settimana che arXiv pubblica oltre questa lista non vengono nemmeno
  guardati. E' una fonte per non restare del tutto scoperti, non una rassegna.
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
| testate RSS (aggiungere/togliere una riga, o cambiare gli URL esclusi di una fonte) | `FEED_RSS` in `raccogli.py` |
| soglia dei punti di Hacker News | `HN_PUNTI_MINIMI` (150) |
| soglia dei voti dei paper | `PAPER_VOTI_MINIMI` (50) |
| le due query GitHub | `RICERCHE_GITHUB` |
| ampiezza della finestra | `GIORNI_FINESTRA` (7) |
| quanti candidati per fonte | `MAX_REPO_PER_RICERCA` (50), `MAX_NOTIZIE_PER_FONTE` (25), `MAX_PAPER_CANDIDATI` (25) |
| distanza minima tra due snapshot per calcolare la crescita | `GIORNI_MINIMI_CONFRONTO` (2) |
| **il criterio, i tetti, il tono** | `prompt.md` |

I tetti — 10 voci tra repo e notizie, 5 per sezione, 3 paper fuori conto —
stanno nel prompt, non nel codice: sono un giudizio, non un limite tecnico. Lo
e' anche la lunghezza delle voci, due righe ovunque tranne che nei paper.

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

Fino al 14 settembre 2026 il conto e' stato 5+5 per cinque giri su sei: il tetto
tagliava, non il criterio. Da adesso i numeri da guardare sono tre, e il terzo
si legge a parte: i paper non competono con gli altri due, quindi non dicono
niente sul criterio — dicono solo quanto e' diventata lunga la mail. Sono la
cosa da pesare il 19 ottobre.
