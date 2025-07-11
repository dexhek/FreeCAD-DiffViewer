# FreeCAD-DiffViewer

**Strumento di confronto geometrico per file STEP in FreeCAD**

Un potente script Python che permette di confrontare visivamente due modelli 3D in formato STEP, evidenziando le differenze geometriche con codifica a colori.

## 🎯 Caratteristiche Principali

- **Confronto Geometrico Preciso**: Analizza le differenze tra due modelli STEP utilizzando operazioni booleane avanzate
- **Visualizzazione Intuitiva**: Codifica a colori per identificare immediatamente:
  - 🟢 **Verde**: Parti aggiunte nel nuovo modello
  - 🔴 **Rosso**: Parti rimosse dal modello originale  
  - 🔵 **Blu**: Parti invariate (comuni ad entrambi i modelli)
- **Gestione Errori Robusta**: Controlli di validità e tolleranze configurabili
- **Report Dettagliato**: Calcolo automatico dei volumi delle modifiche

## 📋 Requisiti

- **FreeCAD** (versione 0.19 o superiore)
- **Python** integrato in FreeCAD
- Due file STEP aperti da confrontare

## 🚀 Installazione e Utilizzo

### Installazione
1. Scarica il file `step_diff.py`
2. Posizionalo in una cartella accessibile da FreeCAD

### Utilizzo Base
1. **Apri FreeCAD**
2. **Carica i modelli**: Importa almeno due file STEP che vuoi confrontare
3. **Esegui lo script**: 
   - Vai su `Macro` → `Macro...`
   - Seleziona `step_diff.py` ed esegui
4. **Visualizza i risultati**: Un nuovo documento mostrerà il confronto con codifica a colori

### Esempio Pratico
```python
# Lo script si esegue automaticamente sui documenti aperti
# Non sono necessari parametri aggiuntivi
```

## ⚙️ Configurazione

Il comportamento dello script può essere personalizzato modificando le costanti all'inizio del file:

```python
# Colori (RGB 0.0-1.0)
AGGIUNTE_COLORE = (0.0, 1.0, 0.0)    # Verde per aggiunte
RIMOSSE_COLORE = (1.0, 0.0, 0.0)     # Rosso per rimozioni  
INVARIATE_COLORE = (0.2, 0.5, 1.0)   # Blu per parti invariate

# Trasparenze (0-100)
TRASPARENZA_MODIFICHE = 50   # Trasparenza per aggiunte/rimozioni
TRASPARENZA_INVARIATE = 85   # Trasparenza per parti invariate

# Tolleranze
TOLLERANZA_VOLUME = 1e-6        # Volume minimo considerato
TOLLERANZA_GEOMETRICA = 1e-3    # Precisione operazioni booleane
```

## 📊 Output e Interpretazione

### Visualizzazione
- **Documento di Confronto**: Viene creato automaticamente con nome `Confronto_[Doc1]_vs_[Doc2]`
- **Oggetti Separati**: Ogni tipo di modifica è un oggetto distinto per analisi dettagliate

### Report Console
```
📊 RISULTATI CONFRONTO:
→ Invariate: 1250.450 mm³ (Blu, Trasparenza 85%)
→ Aggiunte: 125.230 mm³ (Verde, Trasparenza 50%)  
→ Rimozioni: 89.120 mm³ (Rosso, Trasparenza 50%)
→ Variazione netta: +36.110 mm³
```

## 🔧 Funzionalità Avanzate

### Gestione Multi-Corpo
- Unisce automaticamente tutti i corpi solidi in ciascun documento
- Supporta geometrie complesse e assemblati

### Validazione Automatica
- Controllo validità delle geometrie
- Filtro automatico di volumi insignificanti
- Gestione errori nelle operazioni booleane

### Ottimizzazioni
- Pulizia automatica della geometria (`removeSplitter`)
- Tolleranze configurabili per diversi livelli di precisione
- Logging dettagliato per debugging

## 🛠️ Risoluzione Problemi

### Errori Comuni

**"Apri almeno due documenti STEP"**
- Assicurati di aver importato almeno due file STEP in FreeCAD

**"Non sono stati trovati corpi solidi validi"**
- Verifica che i file STEP contengano geometrie 3D valide
- Controlla che i modelli non siano vuoti o corrotti

**Operazioni booleane fallite**
- Aumenta `TOLLERANZA_GEOMETRICA` per geometrie complesse
- Verifica che i modelli non abbiano auto-intersezioni

### Ottimizzazione Prestazioni
- Per modelli molto grandi, aumenta `TOLLERANZA_VOLUME`
- Riduci la precisione se non necessaria per velocizzare l'elaborazione

## 📝 Casi d'Uso

- **Controllo Qualità**: Verifica modifiche tra versioni di un progetto
- **Reverse Engineering**: Confronto tra modello originale e scansione 3D
- **Validazione CAD**: Controllo differenze dopo operazioni di modellazione
- **Analisi Evolutiva**: Tracking delle modifiche nel tempo

## 🤝 Contributi

I contributi sono benvenuti! Per contribuire:

1. Fai un fork del repository
2. Crea un branch per la tua feature (`git checkout -b feature/AmazingFeature`)
3. Committa le modifiche (`git commit -m 'Add some AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Apri una Pull Request

## 📄 Licenza

Questo progetto è distribuito sotto licenza MIT. Vedi il file `LICENSE` per i dettagli.

## 🙏 Riconoscimenti

- **FreeCAD Community** per l'eccellente piattaforma CAD open source
- **OpenCASCADE** per le potenti operazioni geometriche

---

**Sviluppato con ❤️ per la community FreeCAD**
