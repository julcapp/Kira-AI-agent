"""Read-only catalog; availability is not implied by listing a channel."""
from dataclasses import dataclass
from types import MappingProxyType
from .social import Channel, DisabledAdapter, SocialAdapter

@dataclass(frozen=True)
class ChannelSpec:
    channel: Channel
    label: str
    status: str = "planned"

CHANNELS = MappingProxyType({
    channel: ChannelSpec(channel, label)
    for channel, label in (
        (Channel.VK, "VK"), (Channel.MAX, "MAX"),
        (Channel.TELEGRAM, "Telegram"), (Channel.YOUTUBE, "YouTube"),
        (Channel.TIKTOK, "TikTok"), (Channel.INSTAGRAM, "Instagram"),
        (Channel.DZEN, "Дзен"), (Channel.OK, "Одноклассники"),
        (Channel.RUTUBE, "Rutube"), (Channel.WEB, "Web"),
        (Channel.EMAIL, "Email"),
    )
})

def get_adapter(channel: Channel) -> SocialAdapter:
    if not isinstance(channel, Channel) or channel not in CHANNELS:
        raise ValueError("Unknown channel")
    return DisabledAdapter(channel)
