[English](README.md)

# safe-sheet-sync

Una libreria Python che sincronizza un foglio di calcolo con un archivio di record senza distruggere niente. Ha un dry run, un aggiornamento che non cancella mai dati e il ripristino dalle versioni salvate. Le basta la libreria standard, più pytest per i test.

Autore: Lorenzo Algeri

## Il giorno in cui sei biglietti sono stati sovrascritti

Avevo costruito un'app web per i biglietti da visita digitali: ogni dipendente di un gruppo di aziende ha la sua pagina, che si apre avvicinando il telefono a un tag NFC o inquadrando un QR code. L'elenco del personale era in un foglio di calcolo, e per caricarlo nell'app ho scritto degli script.

Il primo import ha sovrascritto i record che c'erano già. In un comando di ispezione avevo lasciato una riga che eseguiva lo script invece di caricarlo e basta. Sei biglietti esistenti hanno perso i campi che il foglio non ha. Li ho recuperati tutti dalla cronologia delle versioni che il database teneva per ogni modifica, quindi non si è perso nessun dato.

Qui ho riscritto la parte che decide cosa cambiare, su un esempio inventato: gli iscritti di una biblioteca di quartiere. Il codice originale non c'è. Da quel giorno mi sono dato tre regole.

1. Il dry run e la scrittura vera usano lo stesso piano. `plan()` calcola cosa verrebbe creato, aggiornato o lasciato com'è, senza scrivere niente. `apply()` prende quel piano e fa solo quello che c'è scritto. Nel codice non c'è una seconda strada che possa fare qualcosa di diverso da quello che è stato stampato.
2. La sincronizzazione non cancella mai niente. Se nel foglio una cella è vuota, il campo pieno resta com'è. I campi che il foglio non gestisce (`notes` e `loan_limit` nell'esempio), una volta creato il record, non si toccano più. I tag aggiunti a mano restano. Se un record sparisce dal foglio viene segnalato, mai cancellato.
3. Prima di toccare un record se ne salva una versione. `restore()` rimette una versione precedente, ma prima salva lo stato che sta per sostituire, così anche un ripristino si può annullare.

## Provarlo in 5 minuti

Ti serve Python 3.9 o più recente.

```
pip install pytest
python -m pytest
python sync.py --dry-run example/members.csv
python sync.py example/members.csv
python sync.py example/members.csv
```

Il primo comando di sincronizzazione elenca 12 iscritti da creare, senza scrivere niente. Il secondo li scrive in `store.json`. Il terzo non ha più niente da fare.

Adesso passiamo al foglio con i casi interessanti. Apri `store.json`, scrivi un testo qualsiasi nel campo `notes` di `LB-0004`, poi lancia:

```
python sync.py --dry-run example/members_march.csv
```

Il piano che esce è questo:

```
PLAN: 1 to create, 4 to update, 5 unchanged, 2 not in sheet, 4 rows skipped

CREATE (1)
  + LB-0013  Mona Newmember | north | adult

UPDATE (4)
  ~ LB-0002  Ben Sample
      phone: 000 000 0002 -> 000 000 0102
  ~ LB-0003  Cora Example
      phone: (empty) -> 000 000 0003
  ~ LB-0005  Eve Fictional
      branch: north -> central
  ~ LB-0007  Gus Mock
      tags: history -> history, poetry

UNCHANGED (5)
  LB-0001, LB-0004, LB-0006, LB-0009, LB-0011

NOT IN SHEET, reported only, nothing is deleted (2)
  ? LB-0008
  ? LB-0012

SKIPPED ROWS (4)
  ! data row 8: no card number
  ! data row 10 LB-0009: duplicate of data row 9, same values
  ! data row 11 LB-0010: conflicting duplicate rows, record left alone
  ! data row 12 LB-0010: conflicting duplicate rows, record left alone
```

Cosa notare:

- `LB-0001` ha lo stesso numero di telefono scritto in un altro formato, quindi per la sincronizzazione non è cambiato niente.
- `LB-0004` nel foglio non ha il telefono. Quello salvato resta, e resta anche la nota che hai scritto tu.
- `LB-0010` compare due volte con valori diversi. Invece di tirare a indovinare, la sincronizzazione lascia stare il record e spiega perché.
- `LB-0008` risulta "not in sheet" solo perché nella sua riga manca il numero di tessera, e chi legge il piano lo vede.

Per applicarlo, lancia lo stesso comando senza `--dry-run`: il piano stampato è identico. Poi:

```
python sync.py --history LB-0002
python sync.py --restore LB-0002 1
```

## A cosa serve ogni file

```
sync.py              command line
safesync/core.py     plan, apply, restore
safesync/store.py    in-memory store with versions, JSON load and save
safesync/report.py   turns a plan into text
example/             two invented sheets
tests/               43 tests
```

## Cosa ho tolto, e perché

L'app che ho costruito ha un database, un login, un editor, le pagine pubbliche e la logica che decide quali campi vede un visitatore. Qui non c'è niente di tutto questo. Non c'è accesso alla rete e i dati sono finti: tutti i nomi dell'esempio sono inventati. Nel repository non ci sono nemmeno credenziali.

I motivi sono due. Quelle parti mostrerebbero com'è fatta l'app in produzione, e non sta a me pubblicarlo. E poi non sono la parte interessante: a rompersi è stata la logica che decide, quindi ho riscritto quella, con un semplice dizionario al posto del database.

C'è un test (`tests/test_no_leaks.py`) che cerca nel repository indirizzi, percorsi, chiavi o parole private. Qualcosa gli può sfuggire, quindi prima di pubblicare rileggo comunque le differenze a mano.

## L'app originale in numeri

Li ho contati sul repository originale il 20 novembre 2026:

- 48 commit su tutti i rami, dal 24 aprile al 21 ottobre 2026. In 31 Claude compare come co-autore.
- Il primo import ha sovrascritto 6 biglietti esistenti su 6, e dalla cronologia delle versioni sono tornati tutti e 6.
- 62 casi di test in 6 file, contati con grep, senza eseguirli. Nessuno copriva gli script di import e sincronizzazione, che qui invece hanno 43 test.
- Un piano di sistemazione in 9 fasi ordinate per rischio, stimato in tutto 27-30 ore e uscito da una revisione del codice su 7 aree. All'ultimo controllo erano fatte solo la fase 0 e una parte della fase 1.

## Prima la revisione, poi i test

Prima di correggere qualsiasi cosa ho chiesto a Claude di rivedere tutto il codice e di pianificare le correzioni in fasi. Il piano prevedeva di dividere il lavoro tra subagenti e di fare un controllo prima di considerare finito un task. Dell'incidente dell'import ho scritto causa, recupero e correzione, e la correzione è diventata la regola che trovi sopra: ogni script che scrive parte come dry run. Da allora nel mio modo di lavorare sono cambiate due cose. Ogni script che scrive dati ha un dry run, e prima di lanciarlo davvero lo guardo. Prima di toccare dati veri salvo una copia o una versione da cui ripartire.

Questo estratto l'ho scritto allo stesso modo. Prima i test, come file, e li ho visti fallire quando il codice ancora non c'era. Poi Claude Code ha scritto il codice finché non sono passati. Le regole e i controlli li ho decisi io.

## Limiti

- I record si abbinano su una sola colonna, senza abbinamenti approssimati.
- I tag si possono solo aggiungere: se ne togli uno dal foglio, nell'archivio resta.
- Il controllo sui piani scaduti lavora campo per campo. Non è un lock, quindi due sincronizzazioni lanciate insieme possono ancora pestarsi i piedi.
- L'archivio è un file JSON caricato tutto in memoria: serve solo a far vedere la logica.
- Il confronto dei telefoni ignora un prefisso `39` iniziale e tutto quello che non è una cifra. Gli altri formati vengono confrontati come semplici cifre.
- Le regole vengono dall'originale, ma non ho mai fatto girare questo codice e l'originale fianco a fianco.

## Licenza

MIT. Vedi `LICENSE`.
