"""
NLQueryHandler - Natural Language Query Processing.

Verarbeitet natürlichsprachliche Anfragen zu CAD-Daten
mittels Pattern-Matching und optionalem LLM.
"""
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from apps.core.handlers.base import (
    BaseCADHandler,
    CADHandlerResult,
    CADHandlerError,
    HandlerStatus,
)
from .nl_learning import get_learning_store
from .use_case_tracker import get_use_case_tracker

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """Erkannte Absichten aus NL-Queries."""
    ROOM_LIST = "room_list"           # "Zeige alle Räume"
    ROOM_AREA = "room_area"           # "Wie groß ist Raum X?"
    TOTAL_AREA = "total_area"         # "Gesamtfläche?"
    LAYER_INFO = "layer_info"         # "Welche Layer gibt es?"
    ENTITY_COUNT = "entity_count"     # "Wie viele Linien?"
    DIMENSION_INFO = "dimension_info" # "Welche Maße?"
    DOOR_COUNT = "door_count"         # "Wie viele Türen?"
    WINDOW_COUNT = "window_count"     # "Wie viele Fenster?"
    QUALITY_CHECK = "quality_check"   # "Prüfe Qualität"
    EXPORT = "export"                 # "Exportiere als JSON"
    UNKNOWN = "unknown"


@dataclass
class ParsedQuery:
    """Ergebnis der Query-Analyse."""
    original: str
    intent: QueryIntent
    entities: dict
    confidence: float
    

class NLQueryHandler(BaseCADHandler):
    """
    Handler für Natural Language Queries.
    
    Funktionen:
    - Pattern-basierte Intent-Erkennung
    - Entity-Extraktion (Raumnamen, Zahlen, etc.)
    - Optional: LLM-Unterstützung für komplexe Queries
    - Routing zu passenden Sub-Handlern
    
    Input:
        query: Natürlichsprachliche Anfrage
        use_llm: Optional - LLM für komplexe Queries nutzen
        loader: Optional - CADLoaderService (von CADFileInputHandler)
    
    Output:
        intent: Erkannte Absicht
        entities: Extrahierte Entitäten
        response: Generierte Antwort
        next_handler: Empfohlener nächster Handler
    """
    
    name = "NLQueryHandler"
    description = "Natural Language Query Processing mit Pattern-Matching + LLM"
    required_inputs = ["query"]
    optional_inputs = ["use_llm", "loader", "format"]
    
    # Pattern-Definitionen für Intent-Erkennung
    PATTERNS = {
        QueryIntent.ROOM_LIST: [
            r"(zeig|list|welche).*(räume|zimmer|raum)",
            r"raumliste",
            r"alle räume",
        ],
        QueryIntent.ROOM_AREA: [
            r"(wie groß|fläche|größe).*(raum|zimmer)",
            r"(raum|zimmer).*(\d+)?\s*(m²|qm|quadrat)",
            r"wieviel.*(m²|qm)",
        ],
        QueryIntent.TOTAL_AREA: [
            r"gesamt.*fläche",
            r"total.*area",
            r"wie groß.*gesamt",
            r"gesamtgröße",
        ],
        QueryIntent.LAYER_INFO: [
            r"(welche|zeig|list).*layer",
            r"layer.*(info|liste|übersicht)",
            r"ebenen",
        ],
        QueryIntent.ENTITY_COUNT: [
            r"wie viele.*(linien|kreise|bögen|texte|entities)",
            r"anzahl.*(linien|elemente)",
            r"zähle",
        ],
        QueryIntent.DIMENSION_INFO: [
            r"(welche|zeig).*maße",
            r"bemaßung",
            r"dimensionen",
            r"abmessungen",
        ],
        QueryIntent.DOOR_COUNT: [
            r"(wie viele|anzahl|zähle).*türen",
            r"türen.*zählen",
        ],
        QueryIntent.WINDOW_COUNT: [
            r"(wie viele|anzahl|zähle).*fenster",
            r"fenster.*zählen",
        ],
        QueryIntent.QUALITY_CHECK: [
            r"(prüf|check|validier).*qualität",
            r"fehler.*(finden|suchen)",
            r"probleme",
        ],
        QueryIntent.EXPORT: [
            r"export.*(json|excel|csv|pdf)",
            r"speicher.*als",
            r"download",
        ],
    }
    
    def execute(self, input_data: dict) -> CADHandlerResult:
        """Verarbeitet NL-Query."""
        result = CADHandlerResult(
            success=True,
            handler_name=self.name,
            status=HandlerStatus.RUNNING,
        )
        
        query = input_data.get("query", "").strip()
        use_llm = input_data.get("use_llm", False)
        loader = input_data.get("_loader") or input_data.get("loader")
        learn_intent = input_data.get("learn_intent")  # For feedback/learning
        
        if not query:
            result.add_error("Keine Anfrage angegeben")
            return result
        
        # Learning: If user provides correction, store it
        learning_store = get_learning_store()
        if learn_intent:
            learning_store.learn(query, learn_intent, source="user_feedback")
            result.data["learned"] = True
            result.data["response"] = f"✅ Gelernt: '{query}' → {learn_intent}"
            result.status = HandlerStatus.SUCCESS
            return result
        
        # 1. Check learned patterns first
        learned_intent = learning_store.get_intent(query)
        if learned_intent:
            try:
                parsed = ParsedQuery(
                    original=query,
                    intent=QueryIntent(learned_intent),
                    entities=self._extract_entities(query),
                    confidence=0.9,
                )
                result.data["source"] = "learned"
                logger.info(f"[{self.name}] Using learned intent: {learned_intent}")
            except ValueError:
                learned_intent = None
        
        # 2. Pattern-based parsing if not learned
        if not learned_intent:
            parsed = self._parse_query(query)
        
        result.data["original_query"] = query
        result.data["intent"] = parsed.intent.value
        result.data["entities"] = parsed.entities
        result.data["confidence"] = parsed.confidence
        
        # 3. If unknown, try LLM or suggest learning
        if parsed.intent == QueryIntent.UNKNOWN:
            if use_llm:
                parsed = self._parse_with_llm(query)
                result.data["used_llm"] = True
            else:
                # Suggest similar learned queries
                suggestions = learning_store.get_suggestions(query, limit=3)
                if suggestions:
                    result.data["suggestions"] = suggestions
                
                # Offer to learn
                result.data["can_learn"] = True
                result.data["available_intents"] = [i.value for i in QueryIntent if i != QueryIntent.UNKNOWN]
        
        # Generate response based on intent
        if loader:
            response = self._generate_response(parsed, loader, input_data)
            result.data["response"] = response
        else:
            result.data["response"] = self._get_intent_description(parsed.intent)
        
        # Suggest next handler
        result.data["next_handler"] = self._suggest_handler(parsed.intent)
        
        result.status = HandlerStatus.SUCCESS
        logger.info(f"[{self.name}] Intent: {parsed.intent.value} (conf: {parsed.confidence:.2f})")
        
        return result
    
    def _parse_query(self, query: str) -> ParsedQuery:
        """Pattern-basierte Query-Analyse."""
        query_lower = query.lower()
        
        best_intent = QueryIntent.UNKNOWN
        best_confidence = 0.0
        entities = {}
        
        for intent, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    # Simple confidence based on pattern specificity
                    confidence = len(pattern) / 50.0  # Normalize
                    confidence = min(confidence, 1.0)
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_intent = intent
        
        # Extract entities
        entities = self._extract_entities(query)
        
        return ParsedQuery(
            original=query,
            intent=best_intent,
            entities=entities,
            confidence=best_confidence if best_intent != QueryIntent.UNKNOWN else 0.0,
        )
    
    def _extract_entities(self, query: str) -> dict:
        """Extrahiert Entitäten aus Query."""
        entities = {}
        
        # Room names
        room_match = re.search(r"(raum|zimmer)\s+(['\"]?)(\w+)\2", query.lower())
        if room_match:
            entities["room_name"] = room_match.group(3)
        
        # Numbers
        numbers = re.findall(r"\d+(?:\.\d+)?", query)
        if numbers:
            entities["numbers"] = [float(n) for n in numbers]
        
        # Layer names
        layer_match = re.search(r"layer\s+(['\"]?)(\w+)\1", query.lower())
        if layer_match:
            entities["layer_name"] = layer_match.group(2)
        
        # Export format
        format_match = re.search(r"(json|excel|csv|pdf)", query.lower())
        if format_match:
            entities["export_format"] = format_match.group(1)
        
        return entities
    
    def _parse_with_llm(self, query: str) -> ParsedQuery:
        """LLM-basierte Query-Analyse (Fallback)."""
        try:
            from apps.core.services.llm_client import generate_text
            
            prompt = f"""Analysiere diese CAD-bezogene Anfrage und extrahiere:
1. Intent (room_list, room_area, total_area, layer_info, entity_count, dimension_info, door_count, window_count, quality_check, export, unknown)
2. Entities (Raumnamen, Zahlen, Layer-Namen, etc.)

Anfrage: "{query}"

Antwort als JSON:
{{"intent": "...", "entities": {{...}}, "confidence": 0.0-1.0}}"""
            
            response = generate_text(prompt, max_tokens=200)
            # Parse JSON response...
            
        except Exception as e:
            logger.warning(f"LLM parsing failed: {e}")
        
        # Fallback to unknown
        return ParsedQuery(
            original=query,
            intent=QueryIntent.UNKNOWN,
            entities={},
            confidence=0.0,
        )
    
    def _generate_response(self, parsed: ParsedQuery, loader, input_data: dict) -> str:
        """Generiert Antwort basierend auf Intent."""
        try:
            if parsed.intent == QueryIntent.ROOM_LIST:
                rooms = loader.get_rooms()
                if rooms:
                    room_names = [r.get("name", "Unbekannt") for r in rooms[:10]]
                    return f"Gefundene Räume: {', '.join(room_names)}"
                return "Keine Räume erkannt"
            
            elif parsed.intent == QueryIntent.TOTAL_AREA:
                areas = loader.get_room_areas()
                if areas:
                    # Get units from analysis to determine conversion factor
                    try:
                        analysis = loader.get_analysis()
                        units = getattr(analysis, 'units', 'Unknown')
                    except:
                        units = 'Unknown'
                    
                    total_raw = sum(a.get("area", 0) for a in areas)
                    
                    # Smart unit conversion based on detected units and magnitude
                    if units and 'mm' in str(units).lower():
                        total = total_raw / 1_000_000  # mm² to m²
                    elif units and 'cm' in str(units).lower():
                        total = total_raw / 10_000  # cm² to m²
                    elif total_raw > 100_000:  # Likely mm²
                        total = total_raw / 1_000_000
                    elif total_raw > 100:  # Likely cm² or raw m²
                        total = total_raw if total_raw < 10000 else total_raw / 10_000
                    else:  # Already in m² or very small
                        total = total_raw
                    
                    return f"Geschätzte Gesamtfläche: {total:.1f} m² ({len(areas)} Flächen)"
                return "Keine geschlossenen Flächen gefunden (LWPOLYLINE)"
            
            elif parsed.intent == QueryIntent.LAYER_INFO:
                layers = loader.get_layers()
                layer_names = [l.get("name", "?") for l in layers[:15]]
                return f"Layer ({len(layers)}): {', '.join(layer_names)}"
            
            elif parsed.intent == QueryIntent.ENTITY_COUNT:
                stats = loader.get_statistics()
                counts = stats.get("entity_counts", {})
                parts = [f"{k}: {v}" for k, v in list(counts.items())[:5]]
                return f"Entities: {', '.join(parts)}"
            
            elif parsed.intent == QueryIntent.DOOR_COUNT:
                doors = loader.get_doors()
                count = len(doors)
                if count == 0:
                    # Track as potential use case
                    tracker = get_use_case_tracker()
                    uc = tracker.report_empty_result(
                        query=parsed.original,
                        intent="door_count",
                        result_type="türen",
                        context={"loader_type": "dxf"}
                    )
                    return f"🚪 Keine Türen erkannt. [Feature-Request #{uc.request_count}x gemeldet]"
                return f"Erkannte Türen: {count}"
            
            elif parsed.intent == QueryIntent.WINDOW_COUNT:
                windows = loader.get_windows()
                count = len(windows)
                if count == 0:
                    # Track as potential use case
                    tracker = get_use_case_tracker()
                    uc = tracker.report_empty_result(
                        query=parsed.original,
                        intent="window_count",
                        result_type="fenster",
                        context={"loader_type": "dxf"}
                    )
                    return f"🪟 Keine Fenster erkannt. [Feature-Request #{uc.request_count}x gemeldet]"
                return f"Erkannte Fenster: {count}"
            
            elif parsed.intent == QueryIntent.QUALITY_CHECK:
                issues = loader.check_quality()
                if issues:
                    return f"Qualitätsprobleme: {len(issues)} gefunden"
                return "Keine Qualitätsprobleme gefunden"
            
            elif parsed.intent == QueryIntent.DIMENSION_INFO:
                dims = loader.get_dimensions()
                return f"Bemaßungen gefunden: {len(dims)}"
            
            else:
                return "Anfrage nicht verstanden. Versuchen Sie: 'Zeige alle Räume' oder 'Wie groß ist die Gesamtfläche?'"
                
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return f"Fehler bei der Verarbeitung: {e}"
    
    def _get_intent_description(self, intent: QueryIntent) -> str:
        """Beschreibung für Intent ohne Loader."""
        descriptions = {
            QueryIntent.ROOM_LIST: "Raumliste wird angefordert",
            QueryIntent.ROOM_AREA: "Raumfläche wird abgefragt",
            QueryIntent.TOTAL_AREA: "Gesamtfläche wird berechnet",
            QueryIntent.LAYER_INFO: "Layer-Informationen werden abgefragt",
            QueryIntent.ENTITY_COUNT: "Entity-Zählung wird durchgeführt",
            QueryIntent.DIMENSION_INFO: "Bemaßungen werden extrahiert",
            QueryIntent.DOOR_COUNT: "Türen werden gezählt",
            QueryIntent.WINDOW_COUNT: "Fenster werden gezählt",
            QueryIntent.QUALITY_CHECK: "Qualitätsprüfung wird durchgeführt",
            QueryIntent.EXPORT: "Export wird vorbereitet",
            QueryIntent.UNKNOWN: "Anfrage nicht erkannt",
        }
        return descriptions.get(intent, "Unbekannt")
    
    def _suggest_handler(self, intent: QueryIntent) -> str:
        """Empfiehlt nächsten Handler."""
        mapping = {
            QueryIntent.ROOM_LIST: "RoomAnalysisHandler",
            QueryIntent.ROOM_AREA: "RoomAnalysisHandler",
            QueryIntent.TOTAL_AREA: "MassenHandler",
            QueryIntent.DOOR_COUNT: "RoomAnalysisHandler",
            QueryIntent.WINDOW_COUNT: "RoomAnalysisHandler",
            QueryIntent.QUALITY_CHECK: "RoomAnalysisHandler",
        }
        return mapping.get(intent, "")
