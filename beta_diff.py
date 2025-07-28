import FreeCAD as App
import Part
import logging
from typing import Optional, List, Tuple

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
TRASPARENZA_INVARIATE = 30  # Ridotta per migliore visibilità
TOLLERANZA_VOLUME = 1e-6  # Tolleranza meno restrittiva
TOLLERANZA_GEOMETRICA = 1e-3  # Tolleranza per operazioni booleane
MOSTRA_ORIGINALI = False  # Mostra solo le differenze
# --- FINE CONFIGURAZIONE ---

def get_valid_shapes(doc) -> List[Part.Shape]:
    """Estrae forme valide da un documento con controlli di sicurezza."""
    shapes = []
    for obj in doc.Objects:
        try:
            if (hasattr(obj, 'Shape') and 
                obj.Shape and 
                obj.Shape.isValid() and 
                abs(obj.Shape.Volume) > TOLLERANZA_VOLUME):
                shapes.append(obj.Shape)
        except Exception as e:
            logger.warning(f"Errore nell'elaborazione dell'oggetto {obj.Label}: {e}")
    return shapes

def get_combined_shape(doc) -> Optional[Part.Shape]:
    """Combina tutti i corpi solidi preservando componenti interni."""
    shapes = get_valid_shapes(doc)
    if not shapes:
        return None
    
    if len(shapes) == 1:
        return shapes[0].copy()
    
    # Usa sempre compound per preservare componenti separati
    try:
        compound = Part.makeCompound(shapes)
        print(f"Debug: Creato compound con {len(shapes)} forme")
        return compound
    except Exception as e:
        logger.warning(f"Errore nella creazione compound: {e}")
        return None

def show_error_message(message: str) -> None:
    """Mostra messaggio di errore in GUI o console."""
    if GUI_AVAILABLE:
        from PySide2 import QtWidgets
        QtWidgets.QMessageBox.warning(None, "Errore", message)
    else:
        print(f"❌ {message}")

def get_comparison_documents() -> Tuple[App.Document, App.Document]:
    """Ottiene i documenti per il confronto con validazione migliorata."""
    docs = list(App.listDocuments().values())
    if len(docs) < 2:
        error_msg = "Apri almeno due documenti STEP per eseguire il confronto."
        show_error_message(error_msg)
        raise ValueError(error_msg)
    
    # Filtra documenti che contengono geometrie valide
    valid_docs = []
    for doc in docs:
        shapes = get_valid_shapes(doc)
        if shapes:
            # Verifica che sia effettivamente un documento STEP/geometrico
            has_geometry = any(hasattr(obj, 'Shape') and obj.Shape for obj in doc.Objects)
            if has_geometry:
                valid_docs.append(doc)
    
    if len(valid_docs) < 2:
        error_msg = "Almeno due documenti devono contenere geometrie valide."
        show_error_message(error_msg)
        raise ValueError(error_msg)
    
    return valid_docs[0], valid_docs[1]

def safe_fuse_compound(shape: Part.Shape) -> Part.Shape:
    """Fuse sicuro per compound con fallback."""
    if shape.ShapeType != 'Compound':
        return shape
    
    try:
        # Prova fuse normale
        fused = shape.fuse([])
        if fused and not fused.isNull() and fused.isValid():
            return fused
    except:
        pass
    
    try:
        # Fallback: fuse manuale dei solidi
        solids = [s for s in shape.Solids if s.isValid()]
        if len(solids) == 1:
            return solids[0]
        elif len(solids) > 1:
            result = solids[0]
            for solid in solids[1:]:
                result = result.fuse(solid)
            return result
    except:
        pass
    
    # Ultimo fallback: ritorna il compound originale
    return shape

def simple_boolean_op(shape1: Part.Shape, shape2: Part.Shape, operation: str) -> Optional[Part.Shape]:
    """Operazioni booleane robuste con gestione compound migliorata."""
    try:
        if not all([shape1, shape2]) or any([shape1.isNull(), shape2.isNull()]):
            return None
        
        # Preparazione sicura delle forme
        s1 = safe_fuse_compound(shape1)
        s2 = safe_fuse_compound(shape2)
        
        if not s1 or not s2 or s1.isNull() or s2.isNull():
            return None
        
        if operation == 'common':
            result = s1.common(s2)
        elif operation == 'cut':
            result = s1.cut(s2)
        else:
            return None
        
        # Verifica risultato valido
        if (result and not result.isNull() and 
            hasattr(result, 'Volume') and abs(result.Volume) > TOLLERANZA_VOLUME):
            print(f"Debug: {operation} completato - Volume: {abs(result.Volume):.3f} mm³")
            return result
        
        return None
        
    except Exception as e:
        print(f"Errore in {operation}: {e}")
        return None

def create_comparison_shapes(vecchio_shape: Part.Shape, nuovo_shape: Part.Shape) -> dict:
    """Crea le forme di confronto con gestione errori ottimizzata."""
    try:
        # Pre-validazione forme con debug
        for name, shape in [("vecchio", vecchio_shape), ("nuovo", nuovo_shape)]:
            if not shape or shape.isNull():
                raise ValueError(f"Forma {name} è None o null")
            print(f"Debug: Forma {name} - Volume: {shape.Volume:.6f}, Valida: {shape.isValid()}")
            if abs(shape.Volume) < TOLLERANZA_VOLUME:
                raise ValueError(f"Forma {name} troppo piccola (Volume: {shape.Volume:.9f})")
        
        # Approccio semplice e diretto
        print("Debug: Calcolo intersezioni...")
        invariate = simple_boolean_op(vecchio_shape, nuovo_shape, 'common')
        
        print("Debug: Calcolo aggiunte...")
        aggiunte = simple_boolean_op(nuovo_shape, vecchio_shape, 'cut')
        
        print("Debug: Calcolo rimozioni...")
        rimosse = simple_boolean_op(vecchio_shape, nuovo_shape, 'cut')
        
        shapes = {
            'invariate': invariate,
            'aggiunte': aggiunte,
            'rimosse': rimosse
        }
        
        # Debug risultati con percentuali
        vol_vecchio = abs(vecchio_shape.Volume)
        vol_nuovo = abs(nuovo_shape.Volume)
        
        for name, shape in shapes.items():
            if shape:
                vol = abs(shape.Volume)
                perc_vecchio = (vol / vol_vecchio) * 100 if vol_vecchio > 0 else 0
                perc_nuovo = (vol / vol_nuovo) * 100 if vol_nuovo > 0 else 0
                print(f"Debug: {name} - Volume: {vol:.3f} mm³ ({perc_vecchio:.1f}% vecchio, {perc_nuovo:.1f}% nuovo)")
            else:
                print(f"Debug: {name} - Nessun risultato")
            
        return shapes
        
    except Exception as e:
        logger.error(f"Errore nelle operazioni booleane: {e}")
        raise

def main():
    """Funzione principale della macro."""
    try:
        # Ottieni i documenti per il confronto
        doc_old, doc_new = get_comparison_documents()

        # Combina tutti i solidi preservando componenti interni
        print(f"🔄 Elaborazione '{doc_old.Label}' vs '{doc_new.Label}'...")
        vecchio_shape = get_combined_shape(doc_old)
        nuovo_shape = get_combined_shape(doc_new)

        if not vecchio_shape or not nuovo_shape:
            missing = []
            if not vecchio_shape: missing.append(f"'{doc_old.Label}'")
            if not nuovo_shape: missing.append(f"'{doc_new.Label}'")
            raise ValueError(f"Nessuna geometria valida trovata in: {', '.join(missing)}")
        
        print(f"Debug: Forme caricate - Vecchio: {vecchio_shape.Volume:.6f} mm³, Nuovo: {nuovo_shape.Volume:.6f} mm³")

        # Crea nuovo documento per il confronto
        doc_cmp = App.newDocument(f"Confronto_{doc_old.Label}_vs_{doc_new.Label}")

        # Calcola le forme di confronto
        shapes = create_comparison_shapes(vecchio_shape, nuovo_shape)

        # Crea oggetti solo per le differenze
        shape_configs = [
            ('invariate', 'Invariate', INVARIATE_COLORE, TRASPARENZA_INVARIATE),
            ('aggiunte', 'Aggiunte', AGGIUNTE_COLORE, TRASPARENZA_MODIFICHE),
            ('rimosse', 'Rimosse', RIMOSSE_COLORE, TRASPARENZA_MODIFICHE)
        ]
        
        created_objects = []
        for key, name, color, transparency in shape_configs:
            shape = shapes.get(key)
            if shape and not shape.isNull():
                obj = doc_cmp.addObject("Part::Feature", name)
                obj.Shape = shape
                if GUI_AVAILABLE and hasattr(obj, 'ViewObject'):
                    obj.ViewObject.ShapeColor = color
                    obj.ViewObject.Transparency = transparency
                    obj.ViewObject.Visibility = True
                created_objects.append(obj)
                print(f"✓ Creato oggetto '{name}' - Volume: {abs(shape.Volume):.3f} mm³")
        
        if not created_objects:
            logger.warning("Nessuna differenza significativa trovata")

        # Finalizza il documento
        try:
            doc_cmp.recompute()
            if GUI_AVAILABLE and hasattr(App, 'Gui') and App.Gui.ActiveDocument:
                Gui.SendMsgToActiveView("ViewFit")
                Gui.activeDocument().activeView().viewIsometric()
        except Exception as e:
            logger.warning(f"Errore nella visualizzazione: {e}")

        # Report finale
        volumi = {
            'invariate': shapes['invariate'].Volume if shapes['invariate'] else 0,
            'aggiunte': shapes['aggiunte'].Volume if shapes['aggiunte'] else 0,
            'rimosse': shapes['rimosse'].Volume if shapes['rimosse'] else 0
        }

        print(f"\n✅ Confronto completato: '{doc_old.Label}' vs '{doc_new.Label}'")
        for nome, volume in volumi.items():
            if volume > 0:
                print(f"  {nome.capitalize()}: {abs(volume):.3f} mm³")

    except Exception as e:
        logger.error(f"Errore durante l'esecuzione: {e}")
        raise

if __name__ == "__main__":
    main()
