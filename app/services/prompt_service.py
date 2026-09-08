import json
from pathlib import Path
from typing import List

from app.core.logging import logger
from app.schemas.prompts import Prompt


class PromptNotFoundError(Exception):
    """Excepción lanzada cuando no se encuentra el prompt solicitado (HTTP 404)."""

    def __init__(self, prompt_id: str):
        self.prompt_id = prompt_id
        super().__init__(f"No se encontró el prompt con identificador '{prompt_id}'.")


class PromptService:
    """
    Servicio de gestión y consulta del catálogo de prompts.
    
    Diseñado mediante repositorio desacoplado para permitir en el futuro
    sustituir la fuente de datos estática (JSON) por base de datos relacional
    sin alterar los contratos de servicio ni la API pública.
    """

    def __init__(self, data_path: Path | None = None):
        if data_path is None:
            self._data_path = Path(__file__).resolve().parent.parent / "data" / "default_prompts.json"
        else:
            self._data_path = data_path
        self._cache: dict[str, Prompt] | None = None

    def _load_prompts(self) -> dict[str, Prompt]:
        """Carga los prompts desde el almacenamiento versionado."""
        if self._cache is not None:
            return self._cache

        if not self._data_path.exists():
            logger.error("El catálogo de prompts no existe en la ruta: %s", self._data_path)
            return {}

        try:
            with open(self._data_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            
            prompts_dict: dict[str, Prompt] = {}
            for item in raw_data:
                prompt = Prompt.model_validate(item)
                prompts_dict[prompt.id] = prompt

            self._cache = prompts_dict
            logger.info("Catálogo de prompts cargado exitosamente (%d prompts)", len(prompts_dict))
            return self._cache
        except Exception as exc:
            logger.error("Error al cargar el catálogo de prompts: %s", exc, exc_info=True)
            return {}

    def get_all(self, include_inactive: bool = False) -> List[Prompt]:
        """
        Retorna la lista de prompts disponibles.
        Por defecto sólo devuelve los prompts marcados como activos.
        """
        prompts = list(self._load_prompts().values())
        if not include_inactive:
            return [p for p in prompts if p.is_active]
        return prompts

    def get_by_id(self, prompt_id: str) -> Prompt:
        """
        Obtiene un prompt específico por su ID estable.
        Lanza PromptNotFoundError si no existe.
        """
        prompts = self._load_prompts()
        if prompt_id not in prompts:
            raise PromptNotFoundError(prompt_id)
        return prompts[prompt_id]


prompt_service = PromptService()
