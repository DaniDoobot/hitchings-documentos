import re


def normalize_text(raw_text: str) -> str:
    """
    Normalización conservadora del texto extraído.
    
    Ajusta saltos de línea, espacios sobrantes y caracteres de control inválidos,
    sin modificar vocabulario, ortografía, estructura de párrafos ni semántica.
    """
    if not raw_text:
        return ""

    # Eliminar caracteres nulos o de control no imprimibles (preservando \n y \t)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", raw_text)

    # Estandarizar saltos de línea a \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Limpiar espacios en blanco al final de cada línea
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Colapsar secuencias de más de dos saltos de línea consecutivos
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def calculate_text_metrics(text: str) -> tuple[int, int]:
    """
    Calcula el conteo de palabras y caracteres de un texto.
    
    Retorna:
        (word_count, character_count)
    """
    if not text:
        return 0, 0

    character_count = len(text)
    word_count = len(text.split())

    return word_count, character_count
