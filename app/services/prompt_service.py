import json
from pathlib import Path
from typing import List, Optional
import uuid

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.session import SessionLocal
from app.models.analysis_type import AnalysisType
from app.schemas.prompts import Prompt
from app.services.analysis_type_service import analysis_type_service


class PromptNotFoundError(Exception):
    """Excepción lanzada cuando no se encuentra el prompt solicitado (HTTP 404)."""

    def __init__(self, prompt_id: str):
        self.prompt_id = prompt_id
        super().__init__(f"No se encontró el prompt con identificador '{prompt_id}'.")


class PromptService:
    """
    Servicio de consulta del catálogo de prompts.
    
    En el Bloque 7C, la fuente de verdad es la tabla 'analysis_types' de PostgreSQL,
    manteniendo compatibilidad total con el esquema Prompt histórico.
    """

    def __init__(self, data_path: Path | None = None):
        if data_path is None:
            self._data_path = Path(__file__).resolve().parent.parent / "data" / "default_prompts.json"
        else:
            self._data_path = data_path
        self._cache: dict[str, Prompt] | None = None

    def _to_prompt(self, item: AnalysisType) -> Prompt:
        return Prompt(
            id=item.code,
            name=item.name,
            description=item.description,
            instructions=item.instructions,
            is_active=item.is_active,
            is_system=item.created_by_user_id is None,
            created_at=item.created_at.isoformat(),
            updated_at=item.updated_at.isoformat(),
        )

    def _load_fallback_prompts(self) -> dict[str, Prompt]:
        """Carga los prompts desde el archivo JSON de respaldo si la base de datos no está disponible."""
        if self._cache is not None:
            return self._cache

        if not self._data_path.exists():
            logger.error("El catálogo de prompts de respaldo no existe en: %s", self._data_path)
            return {}

        try:
            with open(self._data_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            prompts_dict: dict[str, Prompt] = {}
            for item in raw_data:
                prompt = Prompt.model_validate(item)
                prompts_dict[prompt.id] = prompt

            self._cache = prompts_dict
            return self._cache
        except Exception as exc:
            logger.error("Error al cargar el catálogo de prompts JSON: %s", exc, exc_info=True)
            return {}

    def get_all(self, include_inactive: bool = False, db: Optional[Session] = None) -> List[Prompt]:
        """
        Retorna la lista de prompts disponibles.
        Por defecto sólo devuelve los prompts marcados como activos.
        """
        if db is not None:
            types = analysis_type_service.list_analysis_types(db, include_inactive=include_inactive)
            return [self._to_prompt(t) for t in types]

        try:
            with SessionLocal() as session:
                types = analysis_type_service.list_analysis_types(session, include_inactive=include_inactive)
                return [self._to_prompt(t) for t in types]
        except Exception as exc:
            logger.warning("Fallo al consultar analysis_types en DB, recurriendo a fallback JSON: %s", exc)
            prompts = list(self._load_fallback_prompts().values())
            if not include_inactive:
                return [p for p in prompts if p.is_active]
            return prompts

    def get_by_id(self, prompt_id: str, db: Optional[Session] = None) -> Prompt:
        """
        Obtiene un prompt específico por su ID estable (código o UUID).
        Lanza PromptNotFoundError si no existe.
        """
        def _find(session: Session) -> Optional[AnalysisType]:
            found = analysis_type_service.get_by_code(session, prompt_id)
            if found is not None:
                return found
            try:
                val_uuid = uuid.UUID(prompt_id)
                return analysis_type_service.get_by_id(session, val_uuid)
            except (ValueError, AttributeError):
                return None

        if db is not None:
            res = _find(db)
            if res is not None:
                return self._to_prompt(res)
            raise PromptNotFoundError(prompt_id)

        try:
            with SessionLocal() as session:
                res = _find(session)
                if res is not None:
                    return self._to_prompt(res)
                raise PromptNotFoundError(prompt_id)
        except PromptNotFoundError:
            raise
        except Exception as exc:
            logger.warning("Fallo al consultar prompt por ID en DB, recurriendo a fallback JSON: %s", exc)
            prompts = self._load_fallback_prompts()
            if prompt_id not in prompts:
                raise PromptNotFoundError(prompt_id)
            return prompts[prompt_id]


prompt_service = PromptService()
