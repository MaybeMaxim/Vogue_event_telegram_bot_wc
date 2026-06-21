from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Question, SupportMessage


async def add_question(session: AsyncSession, tg_id: int, text: str) -> Question:
    q = Question(tg_id=tg_id, text=text)
    session.add(q)
    await session.commit()
    await session.refresh(q)
    return q


async def all_questions(session: AsyncSession) -> list[Question]:
    stmt = select(Question).order_by(Question.created_at)
    return list((await session.execute(stmt)).scalars().all())


async def add_support_message(
    session: AsyncSession,
    tg_id: int,
    full_name: str,
    username: str | None,
    message_type: str,
    text: str,
) -> SupportMessage:
    msg = SupportMessage(
        tg_id=tg_id,
        full_name=full_name,
        username=username,
        message_type=message_type,
        text=text,
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return msg


async def all_support_messages(session: AsyncSession, message_type: str) -> list[SupportMessage]:
    stmt = (
        select(SupportMessage)
        .where(SupportMessage.message_type == message_type)
        .order_by(SupportMessage.created_at)
    )
    return list((await session.execute(stmt)).scalars().all())
