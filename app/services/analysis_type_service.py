from datetime import datetime, timezone
import re
import unicodedata
from typing import List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis_type import AnalysisType
from app.schemas.analysis_types import AnalysisTypeCreateRequest, AnalysisTypeUpdateRequest


DEFAULT_HISTORIC_TYPES = [
    {
        "id": uuid.UUID("a1000000-0000-0000-0000-000000000001"),
        "code": "executive-summary",
        "name": "Resumen ejecutivo",
        "description": "Genera una síntesis clara, concisa y estructurada del propósito, hechos y conclusiones principales del documento.",
        "instructions": "Eres un asistente experto en síntesis documental de alta precisión. Analiza el contenido suministrado y elabora un resumen ejecutivo riguroso siguiendo estas pautas:\n1. Identifica claramente el propósito y contexto general del documento.\n2. Sintetiza los hechos o contenidos principales de forma estructurada.\n3. Destaca las conclusiones esenciales y decisiones clave.\n4. Prioriza en todo momento la información relevante frente a detalles secundarios.\n5. Basa tu análisis estricta y exclusivamente en la información presente en el documento; nunca añadas datos, suposiciones ni afirmaciones que no figuren en él.\n6. Distingue con total nitidez entre los hechos objetivos expuestos y las interpretaciones o valoraciones si procede.",
        "is_active": True,
    },
    {
        "id": uuid.UUID("a1000000-0000-0000-0000-000000000002"),
        "code": "legal-analysis",
        "name": "Análisis jurídico",
        "description": "Analiza de forma estructurada documentación jurídica, identificando partes, pretensiones, fundamentos de derecho y consecuencias legales.",
        "instructions": "Eres un asistente jurídico especializado en análisis riguroso de expedientes y resoluciones judiciales. Analiza el contenido suministrado y estructura tu examen en los siguientes apartados siempre que la información exista en el texto:\n1. Tipo de documento y contexto procesal.\n2. Partes intervinientes (demandante, demandado, recurrentes, letrados, peritos, etc.).\n3. Objeto del procedimiento o cuestión controvertida.\n4. Antecedentes de hecho relevantes.\n5. Hechos principales probados o alegados.\n6. Argumentos y posiciones mantenidas por cada una de las partes.\n7. Fundamentos jurídicos aplicados o discutidos.\n8. Normativa y jurisprudencia expresamente mencionadas.\n9. Decisión, fallo o parte dispositiva.\n10. Implicaciones jurídicas principales y efectos prácticos.\n11. Cuestiones abiertas, riesgos procesales o contingencias detectadas.\n\nREGLAS FUNDAMENTALES:\n- Prohibición absoluta de inventar o suponer datos procesales, fechas o nombres.\n- Si alguna de las secciones anteriores no consta o no puede determinarse a partir del documento, indícalo expresamente como 'No consta en el documento'.\n- Diferencia rigurosamente el contenido explícito del texto respecto de cualquier inferencia jurídica profesional.",
        "is_active": True,
    },
    {
        "id": uuid.UUID("a1000000-0000-0000-0000-000000000003"),
        "code": "key-points",
        "name": "Puntos clave",
        "description": "Extrae de forma esquemática y priorizada los elementos esenciales, decisiones, obligaciones y riesgos del documento.",
        "instructions": "Eres un analista experto en extracción de puntos neurálgicos documentales. Extrae rápidamente y de forma ordenada los elementos esenciales del contenido suministrado:\n1. Listado priorizado por orden de relevancia o impacto.\n2. Hechos y antecedentes más relevantes.\n3. Cifras cuantitativas, importes económicos y fechas límite de mayor trascendencia.\n4. Decisiones adoptadas o acuerdos formalizados.\n5. Obligaciones y compromisos asumidos por cada parte.\n6. Riesgos, penalizaciones o contingencias advertidas.\n7. Próximos hitos, vencimientos o trámites pendientes identificados en el texto.\n\nREGLA: No incorpores información externa ni infieras obligaciones no estipuladas.",
        "is_active": True,
    },
    {
        "id": uuid.UUID("a1000000-0000-0000-0000-000000000004"),
        "code": "timeline",
        "name": "Cronología",
        "description": "Extrae todos los acontecimientos, actos y fechas identificados en el documento en orden cronológico estricto.",
        "instructions": "Eres un especialista en reconstrucción y ordenación cronológica documental. Analiza el documento y extrae todos los acontecimientos temporales ordenados rigurosamente desde el más antiguo al más reciente:\nPara cada hito detectado, especifica de forma clara:\n- Fecha o período exacto (tal y como figura en el documento).\n- Acontecimiento o hecho acaecido.\n- Actores o partes involucradas.\n- Relevancia o repercusión en el contexto del documento.\n\nREGLA ESTRICTA: No inventes ni aproximes fechas que no existan explícitamente en el texto. Si un hecho no tiene fecha exacta pero se deduce un orden relativo, señálalo como 'Fecha no especificada' y ubícalo por orden lógico.",
        "is_active": True,
    },
    {
        "id": uuid.UUID("a1000000-0000-0000-0000-000000000005"),
        "code": "custom-analysis",
        "name": "Análisis personalizado",
        "description": "Configuración base flexible para responder a instrucciones y preguntas específicas definidas por el usuario.",
        "instructions": "Eres un asistente de análisis documental de alta fidelidad. Tu misión es examinar el documento suministrado atendiendo de manera prioritaria y estricta a las instrucciones adicionales proporcionadas por el usuario.\n\nPAUTAS:\n1. Basa tu respuesta exclusivamente en la información contenida en el documento.\n2. Sigue fielmente el enfoque, estructura o preguntas concretas planteadas por el usuario.\n3. No inventes información ni asumas hechos no respaldados por el texto.\n4. Si el documento no contiene datos suficientes para atender la solicitud del usuario, indícalo con total transparencia.",
        "is_active": True,
    },
]


def slugify(text: str) -> str:
    """Convierte un texto en un slug URL-friendly y seguro para códigos."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^\w\s-]", "", ascii_text.lower()).strip()
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug[:50].strip("-") or "tipo-analisis"


class AnalysisTypeService:
    """Servicio de gestión de Tipos de Análisis Documental persistidos en PostgreSQL."""

    def seed_default_types(self, db: Session) -> None:
        """Siembra los 5 tipos históricos si la tabla se encuentra vacía."""
        existing = db.execute(select(AnalysisType).limit(1)).scalar_one_or_none()
        if existing is not None:
            return

        now = datetime.now(timezone.utc)
        for item in DEFAULT_HISTORIC_TYPES:
            analysis_type = AnalysisType(
                id=item["id"],
                code=item["code"],
                name=item["name"],
                description=item["description"],
                instructions=item["instructions"],
                is_active=item["is_active"],
                created_by_user_id=None,
                updated_by_user_id=None,
                created_at=now,
                updated_at=now,
            )
            db.add(analysis_type)
        db.commit()

    def generate_unique_code(self, db: Session, name: str) -> str:
        """Genera un código único a partir del nombre del tipo de análisis."""
        base_slug = slugify(name)
        code = base_slug
        counter = 1

        while True:
            existing = db.execute(
                select(AnalysisType).where(AnalysisType.code == code)
            ).scalar_one_or_none()
            if existing is None:
                return code
            counter += 1
            code = f"{base_slug}-{counter}"

    def list_analysis_types(
        self,
        db: Session,
        include_inactive: bool = True,
    ) -> List[AnalysisType]:
        """Obtiene el listado de tipos de análisis."""
        query = select(AnalysisType)
        if not include_inactive:
            query = query.where(AnalysisType.is_active.is_(True))
        query = query.order_by(AnalysisType.created_at.asc())
        return list(db.execute(query).scalars().all())

    def get_by_id(self, db: Session, type_id: uuid.UUID) -> Optional[AnalysisType]:
        """Busca un tipo de análisis por su UUID."""
        return db.execute(
            select(AnalysisType).where(AnalysisType.id == type_id)
        ).scalar_one_or_none()

    def get_by_code(self, db: Session, code: str) -> Optional[AnalysisType]:
        """Busca un tipo de análisis por su código textual estable."""
        return db.execute(
            select(AnalysisType).where(AnalysisType.code == code)
        ).scalar_one_or_none()

    def create(
        self,
        db: Session,
        data: AnalysisTypeCreateRequest,
        user_id: Optional[uuid.UUID],
    ) -> AnalysisType:
        """Crea un nuevo tipo de análisis asignando código único inmutable."""
        code = self.generate_unique_code(db, data.name)
        now = datetime.now(timezone.utc)
        analysis_type = AnalysisType(
            id=uuid.uuid4(),
            code=code,
            name=data.name.strip(),
            description=data.description.strip(),
            instructions=data.instructions.strip(),
            is_active=data.is_active,
            created_by_user_id=user_id,
            updated_by_user_id=user_id,
            created_at=now,
            updated_at=now,
        )
        db.add(analysis_type)
        db.commit()
        db.refresh(analysis_type)
        return analysis_type

    def update(
        self,
        db: Session,
        analysis_type: AnalysisType,
        data: AnalysisTypeUpdateRequest,
        user_id: Optional[uuid.UUID],
    ) -> AnalysisType:
        """Actualiza campos editables. El código permanece inmutable."""
        if data.name is not None:
            analysis_type.name = data.name.strip()
        if data.description is not None:
            analysis_type.description = data.description.strip()
        if data.instructions is not None:
            analysis_type.instructions = data.instructions.strip()
        if data.is_active is not None:
            analysis_type.is_active = data.is_active

        analysis_type.updated_by_user_id = user_id
        analysis_type.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(analysis_type)
        return analysis_type


analysis_type_service = AnalysisTypeService()
