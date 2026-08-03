from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession


async def get_session(request: Request) -> AsyncGenerator[AsyncSession]:
    """generator for database async session"""

    async with request.app.state.session_factory() as session:
        try:
            yield session
            await session.commit()

        except Exception:
            await session.rollback()
            raise


SessionDep = Annotated[AsyncSession, Depends(get_session)]
