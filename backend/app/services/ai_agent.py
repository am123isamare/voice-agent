import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import AnalyticsEvent, Conversation, MemorySlot
from app.db.session import AsyncSessionLocal


class AIAgentService:
    def __init__(self) -> None:
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model

    async def fetch_memory(self, user_id: int) -> List[Dict[str, str]]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MemorySlot).where(MemorySlot.user_id == user_id).order_by(MemorySlot.updated_at.desc()).limit(15)
            )
            return [
                {"role": "system", "content": f"Memory: {slot.key} = {slot.value}"}
                for slot in result.scalars().all()
            ]

    async def persist_message(self, user_id: int, session_id: str, role: str, content: str, language: str = "en") -> None:
        async with AsyncSessionLocal() as session:
            message = Conversation(
                user_id=user_id,
                session_id=session_id,
                role=role,
                content=content,
                source="agent" if role == "assistant" else "user",
                language=language,
            )
            session.add(message)
            await session.commit()

    async def create_chat_response(
        self,
        user_id: int,
        session_id: str,
        user_message: str,
        language: str = "en",
    ) -> Dict[str, Any]:
        memory_messages = await self.fetch_memory(user_id)
        system_prompt = (
            "You are a multilingual enterprise voice agent that provides concise, action-oriented answers, "
            "maintains CRM context, and records memory for future conversations."
        )
        message_payload = [
            {"role": "system", "content": system_prompt},
            *memory_messages,
            {"role": "user", "content": user_message},
        ]

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": message_payload,
                    "temperature": 0.6,
                    "max_tokens": 650,
                    "language": language,
                },
            )
            response.raise_for_status()
            completion = response.json()
            assistant_message = completion["choices"][0]["message"]["content"].strip()

        await asyncio.gather(
            self.persist_message(user_id, session_id, "user", user_message, language),
            self.persist_message(user_id, session_id, "assistant", assistant_message, language),
        )

        await self.record_analytics(user_id, "chat_response", {"session_id": session_id, "language": language})

        return {
            "session_id": session_id,
            "message": assistant_message,
            "language": language,
            "timestamp": datetime.utcnow(),
        }

    async def record_memory(self, user_id: int, key: str, value: str, source: str = "conversation") -> None:
        async with AsyncSessionLocal() as session:
            existing = await session.execute(
                select(MemorySlot).where(MemorySlot.user_id == user_id, MemorySlot.key == key)
            )
            record = existing.scalar_one_or_none()
            if record:
                record.value = value
                record.source = source
                record.updated_at = datetime.utcnow()
            else:
                session.add(
                    MemorySlot(user_id=user_id, key=key, value=value, source=source)
                )
            await session.commit()

    async def record_analytics(self, user_id: int, event_type: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        async with AsyncSessionLocal() as session:
            session.add(AnalyticsEvent(user_id=user_id, event_type=event_type, metadata=metadata or {}))
            await session.commit()
