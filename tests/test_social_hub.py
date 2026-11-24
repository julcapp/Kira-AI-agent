import pytest
from app.integrations.social import AccountScope, Channel, ChannelUnavailable, Draft
from app.integrations.social_registry import CHANNELS, get_adapter

def test_catalog_complete():
    assert set(CHANNELS) == set(Channel)
    assert len(CHANNELS) == 11
    assert all(spec.status == "planned" for spec in CHANNELS.values())

def test_invalid_scope():
    with pytest.raises(ValueError):
        AccountScope("", "a", Channel.VK)
    with pytest.raises(ValueError):
        get_adapter("unknown")

@pytest.mark.asyncio
@pytest.mark.parametrize("channel", list(Channel))
async def test_disabled_by_default(channel):
    scope = AccountScope("org", "a", channel)
    adapter = get_adapter(channel)
    caps = await adapter.get_capabilities(scope)
    assert not caps.connected and not caps.publish and not caps.statistics
    assert not caps.comments and not caps.refresh_token and caps.manual_draft
    assert not await adapter.health_check(scope)
    draft = Draft(scope, "v1", "Example")
    assert await adapter.validate_content(draft)
    with pytest.raises(ChannelUnavailable):
        await adapter.publish(draft, approval_id="example", idempotency_key="example")
    for method in (adapter.connect, adapter.disconnect, adapter.get_statistics,
                   adapter.get_comments, adapter.refresh_token):
        with pytest.raises(ChannelUnavailable):
            await method(scope)
    with pytest.raises(ChannelUnavailable):
        await adapter.get_status(scope, "operation")

@pytest.mark.asyncio
async def test_wrong_channel_rejected():
    with pytest.raises(ValueError):
        await get_adapter(Channel.VK).get_capabilities(
            AccountScope("org", "a", Channel.TELEGRAM))
