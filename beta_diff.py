import FreeCAD as App
import Part
import logging
from typing import Optional, List

# Controllo se FreeCAD GUI è disponibile
try:
    import FreeCADGui as Gui
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

# Configurazione logging
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
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
        
        # La geometria risultante è pronta per l'uso
        
        return result
    except Exception as e:
        logger.warning(f"Errore nella fusione, uso compound: {e}")
        return Part.makeCompound(shapes)

def get_comparison_documents():
    """Ottiene i documenti per il confronto con validazione."""
    docs = list(App.listDocuments().values())
    if len(docs) < 2:
        error_msg = "Apri almeno due documenti STEP per eseguire il confronto."
        if GUI_AVAILABLE:
            from PySide2 import QtWidgets
            QtWidgets.QMessageBox.warning(None, "Errore", error_msg)
        else:
            print(f"❌ {error_msg}")
        raise ValueError(error_msg)
    
    # Filtra documenti che contengono geometrie valide
    valid_docs = [doc for doc in docs if get_valid_shapes(doc)]
    if len(valid_docs) < 2:
        error_msg = "Almeno due documenti devono contenere geometrie valide."
        if GUI_AVAILABLE:
            from PySide2 import QtWidgets
            QtWidgets.QMessageBox.warning(None, "Errore", error_msg)
        else:
            print(f"❌ {error_msg}")
        raise ValueError(error_msg)
    
    return valid_docs[0], valid_docs[1]

def main():
    """Funzione principale della macro."""
    try:
        # Ottieni i documenti per il confronto
        doc_old, doc_new = get_comparison_documents()

        # Unisci tutti i solidi in ciascun documento per un confronto robusto
        print(f"🔄 Elaborazione '{doc_old.Label}' vs '{doc_new.Label}'...")
        vecchio_shape = get_fused_shape(doc_old)
        nuovo_shape = get_fused_shape(doc_new)

        if not vecchio_shape or not nuovo_shape:
            raise ValueError("Non sono stati trovati corpi solidi validi in uno o entrambi i documenti.")


        def create_comparison_shapes(vecchio_shape: Part.Shape, nuovo_shape: Part.Shape):
            """Crea le forme di confronto con gestione errori e ottimizzazioni."""
            def safe_boolean_op(shape1, shape2, operation):
                """Esegue operazioni booleane con gestione errori."""
                try:
                    # Verifica che le forme siano valide
                    if not shape1 or not shape2 or shape1.isNull() or shape2.isNull():
                        return None
                    
                    if operation == 'common':
                        result = shape1.common(shape2)
                    elif operation == 'cut':
                        result = shape1.cut(shape2)
                    else:
                        raise ValueError(f"Operazione non supportata: {operation}")
                    
                    # Verifica che il risultato sia valido
                    if not result or result.isNull():
                        return None
                    
                    return result
                    
                except Exception as e:
                    error_str = str(e)
                    if any(x in error_str for x in ["immutable", "Bnd_Box is void", "hasher mismatch", "Null shape"]):
                        logger.warning(f"Errore geometrico ignorato ({operation}): {e}")
                        return None
                    raise
            
            try:
                # Calcola intersezione (parti invariate)
                invariate_shape = safe_boolean_op(vecchio_shape, nuovo_shape, 'common')
                
                # Calcola aggiunte
                aggiunte_shape = safe_boolean_op(nuovo_shape, vecchio_shape, 'cut')
                
                # Calcola rimozioni
                rimosse_shape = safe_boolean_op(vecchio_shape, nuovo_shape, 'cut')
                
                # Filtra forme con volume significativo
                shapes = {
                    'invariate': invariate_shape if invariate_shape and invariate_shape.Volume > TOLLERANZA_VOLUME else None,
                    'aggiunte': aggiunte_shape if aggiunte_shape and aggiunte_shape.Volume > TOLLERANZA_VOLUME else None,
                    'rimosse': rimosse_shape if rimosse_shape and rimosse_shape.Volume > TOLLERANZA_VOLUME else None
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
                Gui.SendMsgToActiveView("ViewFit")
        except Exception as e:
            logger.warning(f"Errore nella visualizzazione: {e}")

        # Report finale
        volumi = {
            'invariate': shapes['invariate'].Volume if shapes['invariate'] else 0,
            'aggiunte': shapes['aggiunte'].Volume if shapes['aggiunte'] else 0,
            'rimosse': shapes['rimosse'].Volume if shapes['rimosse'] else 0
        }

        print(f"\n✅ Confronto completato: '{doc_old.Label}' vs '{doc_new.Label}'")
        print(f"📊 RISULTATI:")
        print(f"→ Invariate: {volumi['invariate']:.3f} mm³ (Blu)")
        print(f"→ Aggiunte: {volumi['aggiunte']:.3f} mm³ (Verde)")
        print(f"→ Rimozioni: {volumi['rimosse']:.3f} mm³ (Rosso)")
        print(f"→ Variazione netta: {volumi['aggiunte'] - volumi['rimosse']:.3f} mm³")
        
                    
    except Exception as e:
        error_msg = str(e)
        print(f"❌ {error_msg}")
        if GUI_AVAILABLE and "Apri almeno" not in error_msg and "Almeno due" not in error_msg:
            from PySide2 import QtWidgets
            QtWidgets.QMessageBox.critical(None, "Errore", error_msg)

# Esegui la macro
if __name__ == "__main__":
    main()
