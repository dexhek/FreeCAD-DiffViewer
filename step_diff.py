import FreeCAD as App
import Part
import logging
from typing import Optional, List

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- INIZIO CONFIGURAZIONE ---
AGGIUNTE_COLORE = (0.0, 1.0, 0.0)  # Verde
RIMOSSE_COLORE = (1.0, 0.0, 0.0)   # Rosso
INVARIATE_COLORE = (0.2, 0.5, 1.0) # Blu
TRASPARENZA_MODIFICHE = 50  # 0-100 (0=opaco, 100=invisibile)
TRASPARENZA_INVARIATE = 85
TOLLERANZA_VOLUME = 1e-6  # Tolleranza per volumi minimi
TOLLERANZA_GEOMETRICA = 1e-3  # Tolleranza per operazioni booleane
# --- FINE CONFIGURAZIONE ---

def get_valid_shapes(doc) -> List[Part.Shape]:
    """Estrae forme valide da un documento con controlli di sicurezza."""
    shapes = []
    for obj in doc.Objects:
        try:
            if (hasattr(obj, 'Shape') and 
                obj.Shape and 
                obj.Shape.isValid() and 
                obj.Shape.Volume > TOLLERANZA_VOLUME):
                shapes.append(obj.Shape)
        except Exception as e:
            logger.warning(f"Errore nell'elaborazione dell'oggetto {obj.Label}: {e}")
    return shapes

def get_fused_shape(doc) -> Optional[Part.Shape]:
    """Unisce tutti i corpi solidi in un documento con gestione errori migliorata."""
    shapes = get_valid_shapes(doc)
    if not shapes:
        return None
    
    if len(shapes) == 1:
        return shapes[0]
    
    try:
        # Usa fuse invece di compound per una geometria più robusta
        result = shapes[0]
        for shape in shapes[1:]:
            result = result.fuse(shape)
        
        # Pulisci la geometria risultante
        if hasattr(result, 'removeSplitter'):
            result = result.removeSplitter()
        
        return result
    except Exception as e:
        logger.warning(f"Errore nella fusione, uso compound: {e}")
        return Part.makeCompound(shapes)

def get_comparison_documents():
    """Ottiene i documenti per il confronto con validazione."""
    docs = list(App.listDocuments().values())
    if len(docs) < 2:
        raise ValueError("Apri almeno due documenti STEP per eseguire il confronto.")
    
    # Filtra documenti che contengono geometrie valide
    valid_docs = [doc for doc in docs if get_valid_shapes(doc)]
    if len(valid_docs) < 2:
        raise ValueError("Almeno due documenti devono contenere geometrie valide.")
    
    return valid_docs[0], valid_docs[1]

# Ottieni i documenti per il confronto
doc_old, doc_new = get_comparison_documents()

# Unisci tutti i solidi in ciascun documento per un confronto robusto
logger.info(f"Elaborazione documento vecchio: {doc_old.Label}")
vecchio_shape = get_fused_shape(doc_old)
logger.info(f"Elaborazione documento nuovo: {doc_new.Label}")
nuovo_shape = get_fused_shape(doc_new)

if not vecchio_shape or not nuovo_shape:
    raise ValueError("Non sono stati trovati corpi solidi validi in uno o entrambi i documenti.")

# Imposta tolleranza per operazioni booleane
vecchio_shape.Tolerance = TOLLERANZA_GEOMETRICA
nuovo_shape.Tolerance = TOLLERANZA_GEOMETRICA

def create_comparison_shapes(vecchio_shape: Part.Shape, nuovo_shape: Part.Shape):
    """Crea le forme di confronto con gestione errori e ottimizzazioni."""
    try:
        # Calcola intersezione (parti invariate)
        logger.info("Calcolo parti invariate...")
        invariate_shape = vecchio_shape.common(nuovo_shape)
        
        # Calcola aggiunte con pulizia geometrica
        logger.info("Calcolo aggiunte...")
        aggiunte_shape = nuovo_shape.cut(vecchio_shape)
        if hasattr(aggiunte_shape, 'removeSplitter'):
            aggiunte_shape = aggiunte_shape.removeSplitter()
        
        # Calcola rimozioni con pulizia geometrica
        logger.info("Calcolo rimozioni...")
        rimosse_shape = vecchio_shape.cut(nuovo_shape)
        if hasattr(rimosse_shape, 'removeSplitter'):
            rimosse_shape = rimosse_shape.removeSplitter()
        
        # Filtra forme con volume significativo per evitare duplicati
        shapes = {
            'invariate': invariate_shape if invariate_shape.Volume > TOLLERANZA_VOLUME else None,
            'aggiunte': aggiunte_shape if aggiunte_shape.Volume > TOLLERANZA_VOLUME else None,
            'rimosse': rimosse_shape if rimosse_shape.Volume > TOLLERANZA_VOLUME else None
        }
        
        return shapes
        
    except Exception as e:
        logger.error(f"Errore nelle operazioni booleane: {e}")
        raise

# Crea nuovo documento per il confronto
doc_cmp = App.newDocument(f"Confronto_{doc_old.Label}_vs_{doc_new.Label}")

# Calcola le forme di confronto
shapes = create_comparison_shapes(vecchio_shape, nuovo_shape)

# Crea oggetti solo se le forme sono valide
if shapes['invariate']:
    invariate = doc_cmp.addObject("Part::Feature", "Invariate")
    invariate.Shape = shapes['invariate']
    invariate.ViewObject.ShapeColor = INVARIATE_COLORE
    invariate.ViewObject.Transparency = TRASPARENZA_INVARIATE

if shapes['aggiunte']:
    aggiunte = doc_cmp.addObject("Part::Feature", "Aggiunte")
    aggiunte.Shape = shapes['aggiunte']
    aggiunte.ViewObject.ShapeColor = AGGIUNTE_COLORE
    aggiunte.ViewObject.Transparency = TRASPARENZA_MODIFICHE

if shapes['rimosse']:
    rimosse = doc_cmp.addObject("Part::Feature", "Rimosse")
    rimosse.Shape = shapes['rimosse']
    rimosse.ViewObject.ShapeColor = RIMOSSE_COLORE
    rimosse.ViewObject.Transparency = TRASPARENZA_MODIFICHE

# Finalizza il documento
try:
    doc_cmp.recompute()
    if hasattr(App, 'Gui') and App.Gui.ActiveDocument:
        App.Gui.ActiveDocument.ActiveView.fitAll()
except Exception as e:
    logger.warning(f"Errore nella visualizzazione: {e}")

# Report finale
logger.info(f"✅ Confronto completato tra '{doc_old.Label}' e '{doc_new.Label}'.")
volumi = {
    'invariate': shapes['invariate'].Volume if shapes['invariate'] else 0,
    'aggiunte': shapes['aggiunte'].Volume if shapes['aggiunte'] else 0,
    'rimosse': shapes['rimosse'].Volume if shapes['rimosse'] else 0
}

print(f"\n📊 RISULTATI CONFRONTO:")
print(f"→ Invariate: {volumi['invariate']:.3f} mm³ (Blu, Trasparenza {TRASPARENZA_INVARIATE}%)")
print(f"→ Aggiunte: {volumi['aggiunte']:.3f} mm³ (Verde, Trasparenza {TRASPARENZA_MODIFICHE}%)")
print(f"→ Rimozioni: {volumi['rimosse']:.3f} mm³ (Rosso, Trasparenza {TRASPARENZA_MODIFICHE}%)")
print(f"→ Variazione netta: {volumi['aggiunte'] - volumi['rimosse']:.3f} mm³")
