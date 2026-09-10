"""create analysis_types table and seed initial types

Revision ID: 0002_analysis_types
Revises: 0001_initial_auth
Create Date: 2026-09-10 16:00:00.000000

"""
from datetime import datetime, timezone
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_analysis_types'
down_revision: Union[str, None] = '0001_initial_auth'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INITIAL_ANALYSIS_TYPES = [
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


def upgrade() -> None:
    # 1. Crear tabla analysis_types
    analysis_types_table = op.create_table(
        'analysis_types',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('instructions', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('updated_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_analysis_types_code'), 'analysis_types', ['code'], unique=True)

    # 2. Sembrar los 5 tipos de análisis históricos
    now = datetime.now(timezone.utc)
    seed_records = []
    for item in INITIAL_ANALYSIS_TYPES:
        seed_records.append({
            "id": item["id"],
            "code": item["code"],
            "name": item["name"],
            "description": item["description"],
            "instructions": item["instructions"],
            "is_active": item["is_active"],
            "created_by_user_id": None,
            "updated_by_user_id": None,
            "created_at": now,
            "updated_at": now,
        })
    op.bulk_insert(analysis_types_table, seed_records)


def downgrade() -> None:
    op.drop_index(op.f('ix_analysis_types_code'), table_name='analysis_types')
    op.drop_table('analysis_types')
