from datetime import datetime
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.api.deps import get_db, get_current_user, get_current_org
from app.db.models import User, KnowledgeBase
from pydantic import BaseModel, ConfigDict

router = APIRouter()


class KBCreate(BaseModel):
    name: str
    description: str | None = None


class KBRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    org_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.post("/", response_model=KBRead)
async def create_knowledge_base(
    kb_in: KBCreate,
    current_user: User = Depends(get_current_user),
    org_id: UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    # 逻辑已经在 get_current_org 中校验了权限和 RLS
    kb = KnowledgeBase(
        org_id=org_id,
        created_by=current_user.id,
        name=kb_in.name,
        description=kb_in.description,
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return kb


@router.get("/", response_model=List[KBRead])
async def list_knowledge_bases(
    skip: int = 0,
    limit: int = 100,
    org_id: UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    # 依赖 RLS，直接查询即可，只能查到当前 org_id 的数据
    stmt = select(KnowledgeBase).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: UUID,
    org_id: UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # 因为 get_current_org 会注入 RLS，如果 kb 不属于当前 org，
    # 这里的 db.get 可能会返回 None 或在后续操作中报错（取决于 RLS 严格程度）
    # 为稳妥起见，手动校验 org_id
    if kb.org_id != org_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    await db.delete(kb)
    await db.commit()
    return {"status": "ok"}
