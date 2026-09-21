## Repo

### [anthropics/commerce-agents](https://github.com/anthropics/commerce-agents)
Blueprint di riferimento di Anthropic per costruire agenti di shopping e commercio con Claude, con esempi in retail, telecom ed entertainment — utile proprio ora che Amazon ha bloccato l'agente di shopping di Meta (vedi Notizie).

### [shadcn-ui/lint](https://github.com/shadcn-ui/lint)
Linter pensato per agenti: si scrivono le regole del proprio design system Tailwind/shadcn e un coding agent le verifica automaticamente invece che a occhio in review.

### [chenglou/pretext](https://github.com/chenglou/pretext)
Libreria per misurare e disporre testo in modo preciso e veloce, dall'autore di Reason/ReasonML. Utile ovunque serva un layout di testo accurato senza passare dal DOM del browser.

### [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness)
Nuovo harness per agenti di coding di DeepSeek, ad architettura completamente a plugin: alternativa a Claude Code/Codex per chi usa modelli DeepSeek.

### [Tencent/WeMM-Embedding](https://github.com/Tencent/WeMM-Embedding)
Famiglia di modelli di embedding multimodale del team WeChat Vision di Tencent, per ricerca e retrieval che mescola testo, immagini e video.

## Notizie

### [Introducing System One Models and Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
TypeSafe AI lancia i "System One models": modelli piccoli e non-autoregressivi (rispondono in un colpo solo, non parola per parola) per prendere decisioni strutturate in pochi millisecondi invece di far generare testo a un LLM completo. È l'origine della valanga di repo "jev-*" di questa settimana — instradamento, memoria, compattazione del contesto — tutti costruiti sopra.

### [Claude Code now reads AGENTS.md if there is no Claude.md](https://code.claude.com/docs/en/changelog)
Claude Code adotta AGENTS.md, il file di istruzioni già usato da Codex e altri agenti, quando non trova un CLAUDE.md. Un repo può avere una sola configurazione condivisa tra agenti diversi invece di duplicarla.

### [Nvidia announces native GPU programming in Rust](https://developer.nvidia.com/blog/introducing-cuda-rust-two-tracks-for-writing-gpu-kernels/)
Nvidia apre due percorsi ufficiali per scrivere kernel CUDA direttamente in Rust, invece di passare per C/C++ o binding esterni non ufficiali.

### [iOS 27, iPadOS 27, and macOS 27](https://www.apple.com/newsroom/2026/09/major-updates-for-apples-software-platforms-are-now-available/)
Apple rilascia le nuove major version di iOS, iPadOS e macOS: punto di riferimento per chi deve testare e aggiornare le proprie app prima che gli utenti aggiornino i dispositivi.

### [Amazon doesn't trust Meta's Muse AI agent](https://www.theverge.com/tech/998078/amazon-blocks-meta-muse-ai-agent-shopping)
Amazon ha bloccato l'agente di shopping Muse di Meta, citando i termini di servizio contro agenti AI non autorizzati che comprano per conto degli utenti. Primo scontro concreto tra un negozio online e un agente di terzi che compra sopra la sua piattaforma, rilevante per chi sta costruendo agenti di questo tipo.

## Paper

### [SoL-Pi: Recursively Scaling Auto-Research Loops for Efficient Agent Harness](https://arxiv.org/abs/2609.20519)
I coding agent che lavorano da soli per ore (tipo Claude Code o Codex) spendono molti token — le unità di testo che il modello processa, e che si pagano — in lavoro di infrastruttura ripetitivo: gestire il contesto, rileggere file, ricordare cosa è già stato fatto. NVIDIA ha costruito un ciclo automatico che testa tante piccole modifiche a questa infrastruttura su un gran numero di compiti diversi e tiene solo quelle che funzionano ovunque, non solo sul compito su cui sono nate. Applicato sopra Claude Code e Codex, riduce il traffico di token del 44-49% e il costo per ora del lavoro dell'agente di circa un terzo (stimato 8-13 dollari l'ora risparmiati). Per ora è misurato su un solo benchmark (EdgeBench), ma il codice è pubblico e si innesta su harness già esistenti.

### [An Empirical Study of Harness Design for Coding Agents](https://arxiv.org/abs/2609.20804)
Oggi chi costruisce l'harness di un coding agent — l'infrastruttura attorno al modello che decide come pianifica, quali strumenti può chiamare, come gestisce la memoria di contesto — lo fa più per intuito che per dati, perché la letteratura valuta sempre l'harness intero come scatola nera. Questo studio di Zoom smonta un harness minimale e testa 176 combinazioni controllate di tre componenti — pianificazione, strumenti disponibili, gestione del contesto — su quattro modelli e due benchmark standard di settore (SWE-Bench Verified, Terminal-Bench). Il risultato pratico: la gestione del contesto conta soprattutto quando lo spazio disponibile è stretto e serve principalmente a evitare di "rompersi" per overflow, tecniche semplici a regole battono spesso il riassunto fatto da un altro LLM, e la pianificazione aiuta i modelli deboli ma non quelli già forti. Per chi mette mano a un harness proprio sono scelte difendibili con dati, non a sensazione — niente codice pubblico però.

### [Grounded Skill Synthesis from Code at Scale for Agentic Intelligence](https://arxiv.org/abs/2609.05571)
Oggi un agente impara una "skill" — una procedura riusabile, tipo una ricetta salvata — o facendola girare dentro un ambiente specifico, oppure leggendo documentazione scritta a mano che spesso non è mai stata verificata contro codice vero. Questo lavoro di Ant Group estrae automaticamente skill da circa 20mila repository GitHub popolari, ricostruendo ogni procedura da zero a partire dal solo codice e verificandola per confronto con l'originale. Dare in pasto queste skill a un agente, recuperandole al momento giusto, migliora le prestazioni dell'11,7% in media su otto benchmark diversi rispetto a non averle. È rilevante proprio ora che metà delle repo di questa settimana sono raccolte di skill scritte a mano: qui la generazione è automatica e ancorata a codice eseguibile invece che a prompt scritti da qualcuno, e il codice è pubblico.
