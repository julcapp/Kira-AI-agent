"""Social Hub contract. No live transport is enabled by this module."""
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Mapping

class Channel(str, Enum):
    VK = "vk"
    MAX = "max"
    TELEGRAM = "telegram"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    DZEN = "dzen"
    OK = "ok"
    RUTUBE = "rutube"
    WEB = "web"
    EMAIL = "email"

@dataclass(frozen=True)
class AccountScope:
    organization_id: str
    account_id: str
    channel: Channel

    def __post_init__(self):
        if not self.organization_id.strip() or not self.account_id.strip():
            raise ValueError("Account and organization are required")
        if not isinstance(self.channel, Channel):
            raise ValueError("Unknown channel")

@dataclass(frozen=True)
class Capabilities:
    connected: bool = False
    publish: bool = False
    statistics: bool = False
    comments: bool = False
    refresh_token: bool = False
    manual_draft: bool = True

@dataclass(frozen=True)
class Draft:
    scope: AccountScope
    revision: str
    text: str

    def __post_init__(self):
        if not self.revision.strip() or not self.text.strip():
            raise ValueError("Draft revision and text are required")

class SocialAdapter(Protocol):
    async def connect(self, scope: AccountScope) -> None: ...
    async def disconnect(self, scope: AccountScope) -> None: ...
    async def health_check(self, scope: AccountScope) -> bool: ...
    async def get_capabilities(self, scope: AccountScope) -> Capabilities: ...
    async def validate_content(self, draft: Draft) -> tuple[str, ...]: ...
    async def publish(self, draft: Draft, *, approval_id: str, idempotency_key: str) -> str: ...
    async def get_statistics(self, scope: AccountScope) -> Mapping[str, int]: ...
    async def get_comments(self, scope: AccountScope) -> tuple[str, ...]: ...
    async def get_status(self, scope: AccountScope, operation_id: str) -> str: ...
    async def refresh_token(self, scope: AccountScope) -> None: ...

class ChannelUnavailable(RuntimeError):
    pass

class DisabledAdapter:
    """Fail closed until verified transport, authorization and approval services exist."""
    def __init__(self, channel: Channel):
        self.channel = channel

    def _scope(self, scope: AccountScope):
        if scope.channel != self.channel:
            raise ValueError("Channel mismatch")

    async def get_capabilities(self, scope: AccountScope) -> Capabilities:
        self._scope(scope)
        return Capabilities()

    async def health_check(self, scope: AccountScope) -> bool:
        self._scope(scope)
        return False

    async def validate_content(self, draft: Draft) -> tuple[str, ...]:
        self._scope(draft.scope)
        return ("Platform-specific validation unavailable; manual draft only",)

    async def _blocked(self, scope: AccountScope):
        self._scope(scope)
        raise ChannelUnavailable("Live channel integration is disabled")

    async def connect(self, scope: AccountScope):
        await self._blocked(scope)

    async def disconnect(self, scope: AccountScope):
        await self._blocked(scope)

    async def publish(self, draft: Draft, *, approval_id: str, idempotency_key: str):
        await self._blocked(draft.scope)

    async def get_statistics(self, scope: AccountScope):
        await self._blocked(scope)

    async def get_comments(self, scope: AccountScope):
        await self._blocked(scope)

    async def get_status(self, scope: AccountScope, operation_id: str):
        await self._blocked(scope)

    async def refresh_token(self, scope: AccountScope):
        await self._blocked(scope)
