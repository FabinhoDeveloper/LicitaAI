from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Document


def get_user_documents(
    db: Session,
    user_id: int,
    search: Optional[str] = None,
    order_by: str = "created_at_desc",
) -> list[Document]:
    query = db.query(Document).filter(Document.user_id == user_id)

    if search:
        query = query.filter(Document.title.ilike(f"%{search}%"))

    order_map = {
        "created_at_desc": Document.created_at.desc(),
        "created_at_asc": Document.created_at.asc(),
        "title_asc": Document.title.asc(),
        "title_desc": Document.title.desc(),
    }
    order_column = order_map.get(order_by, Document.created_at.desc())
    query = query.order_by(order_column)

    return query.all()


def get_document_by_id(db: Session, document_id: int) -> Optional[Document]:
    return db.query(Document).filter(Document.id == document_id).first()


def create_document(
    db: Session,
    user_id: int,
    title: str,
    doc_type: str = "dfd",
    file_path: Optional[str] = None,
) -> Document:
    document = Document(
        user_id=user_id,
        title=title,
        type=doc_type,
        file_path=file_path,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document
