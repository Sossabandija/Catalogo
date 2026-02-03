"""
Extracción de texto desde PDF usando LLMWhisper (Unstract).

- Si ya existe un .txt asociado al PDF, se usa ese archivo y no se llama a LLMWhisper.
- Si no existe, se extrae con LLMWhisper (modo layout_preserving para extracción espacial) y se guarda el .txt.

Uso:
  from src.llmwhisper_extract import get_pdf_text_as_txt
  text = get_pdf_text_as_txt("pdf/Catalogo_Mamut_2025.pdf")
"""

import os
import sys
from pathlib import Path

# Cliente LLMWhisperer: opcional
LLMWhispererClientV2 = None
try:
    from unstract.llmwhisperer import LLMWhispererClientV2
except (ModuleNotFoundError, ImportError):
    try:
        from llmwhisperer_client import LLMWhispererClientV2
    except (ModuleNotFoundError, ImportError):
        LLMWhispererClientV2 = None

# Configuración por defecto (recomendado: usar variables de entorno)
DEFAULT_BASE_URL = "https://llmwhisperer-api.us-central.unstract.com/api/v2"
DEFAULT_API_KEY = os.environ.get("LLMWHISPERER_API_KEY", "HjCYwtq5w6-wIdCPWXPocgmdqt-uV-gEWy-9dtUQsIw")

_client = None


def get_client():
    """Devuelve el cliente LLMWhisperer si está disponible."""
    global _client
    if _client is not None:
        return _client
    if LLMWhispererClientV2 is None:
        return None
    try:
        base_url = os.environ.get("LLMWHISPERER_BASE_URL_V2", DEFAULT_BASE_URL)
        api_key = os.environ.get("LLMWHISPERER_API_KEY", DEFAULT_API_KEY)
        _client = LLMWhispererClientV2(
            base_url=base_url,
            api_key=api_key,
            logging_level="ERROR",
        )
        return _client
    except Exception as e:
        print(f"Error inicializando LLMWhisperer client: {e}", file=sys.stderr)
        return None


def get_pdf_text_via_llmwhisper(
    pdf_path: str,
    txt_path: str | Path | None = None,
    output_mode: str = "layout_preserving",
    wait_timeout: int = 300,
    pages_per_batch: int = 20,
) -> str:
    """
    Extrae texto del PDF usando LLMWhisper (modo layout_preserving por defecto para extracción espacial).
    Procesa en lotes de páginas para evitar límites de la API.
    Guarda el resultado en txt_path si se indica.
    """
    client = get_client()
    if client is None:
        raise ImportError(
            "LLMWhisperer no disponible. Instala: pip install llmwhisperer-client "
            "y configura LLMWHISPERER_API_KEY si es necesario."
        )

    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")

    # Obtener número total de páginas del PDF
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        doc.close()
        print(f"PDF tiene {total_pages} páginas")
    except ImportError:
        print("PyMuPDF no disponible, extrayendo todo el PDF en una sola llamada...")
        total_pages = None
    
    all_text = []
    
    if total_pages and total_pages > pages_per_batch:
        # Procesar en lotes
        for start_page in range(1, total_pages + 1, pages_per_batch):
            end_page = min(start_page + pages_per_batch - 1, total_pages)
            page_range = f"{start_page}-{end_page}"
            print(f"  Extrayendo páginas {page_range} de {total_pages}...")
            
            result = client.whisper(
                file_path=str(pdf_path),
                mode="high_quality",
                output_mode=output_mode,
                wait_for_completion=True,
                wait_timeout=wait_timeout,
                encoding="utf-8",
                pages_to_extract=page_range,
            )
            
            batch_text = _extract_text_from_result(result)
            if batch_text:
                all_text.append(f"<<< Páginas {page_range} >>>")
                all_text.append(batch_text)
        
        text = "\n".join(all_text)
    else:
        # Procesar todo de una vez
        result = client.whisper(
            file_path=str(pdf_path),
            mode="high_quality",
            output_mode=output_mode,
            wait_for_completion=True,
            wait_timeout=wait_timeout,
            encoding="utf-8",
        )
        text = _extract_text_from_result(result)

    if txt_path is not None:
        txt_path = Path(txt_path)
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        txt_path.write_text(text, encoding="utf-8")
        print(f"Texto guardado en: {txt_path}")

    return text


def _extract_text_from_result(result) -> str:
    """Extrae el texto del resultado de LLMWhisper."""
    text = ""
    if isinstance(result, dict):
        # Primero intentar result_text directo
        text = result.get("result_text")
        
        # Si no, verificar si extraction es un dict con result_text
        if not text:
            extraction = result.get("extraction")
            if isinstance(extraction, dict):
                text = extraction.get("result_text", "")
            elif isinstance(extraction, str):
                text = extraction
        
        # Fallback a "text"
        if not text:
            text = result.get("text", "")
        
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="replace")
        text = text or ""
    
    return text


def get_pdf_text_as_txt(
    pdf_path: str,
    txt_path: str | Path | None = None,
    force_extract: bool = False,
    use_llmwhisper: bool = True,
) -> str:
    """
    Obtiene el texto del PDF para extracción del catálogo.

    - Si txt_path existe y no se fuerza reextracción, lee y devuelve el contenido del .txt
      (no se llama a LLMWhisper).
    - Si no existe el .txt o force_extract=True, extrae con LLMWhisper (layout_preserving),
      guarda en txt_path y devuelve el texto.
    - Si use_llmwhisper=False y no hay .txt, no se usa LLMWhisper (el llamador puede usar PyMuPDF).

    pdf_path: ruta al PDF.
    txt_path: ruta donde guardar/leer el .txt. Por defecto mismo nombre que el PDF con extensión .txt.
    force_extract: si True, reextraer siempre con LLMWhisper y sobrescribir el .txt.
    use_llmwhisper: si True, usar LLMWhisper cuando haga falta extraer; si False, no llamar a la API.

    Returns:
        Texto completo del documento (una línea por línea del PDF en modo layout_preserving).
    """
    pdf_path = Path(pdf_path).resolve()
    if txt_path is None:
        txt_path = pdf_path.with_suffix(".txt")
    else:
        txt_path = Path(txt_path).resolve()

    if not force_extract and txt_path.exists():
        return txt_path.read_text(encoding="utf-8")

    if use_llmwhisper and get_client() is not None:
        return get_pdf_text_via_llmwhisper(
            str(pdf_path),
            txt_path=str(txt_path),
            output_mode="layout_preserving",
        )

    if force_extract or not txt_path.exists():
        raise FileNotFoundError(
            f"No existe el archivo de texto '{txt_path}' y no se puede extraer: "
            "instala llmwhisperer-client y configura la API, o genera antes el .txt."
        )
    return txt_path.read_text(encoding="utf-8")
