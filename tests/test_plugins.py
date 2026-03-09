import pytest

from indigoapi.analyses.registry import get_analysis


@pytest.mark.asyncio
async def test_sync_plugin():

    fn = get_analysis("double")

    result = await fn(5)

    assert result == 10


@pytest.mark.asyncio
async def test_async_plugin():

    fn = get_analysis("sleep")

    result = await fn({"seconds": 0})

    assert result == "done"


@pytest.mark.asyncio
async def test_sync_plugin_zero():

    fn = get_analysis("double")

    result = await fn({"value": 0})

    assert result == 0


@pytest.mark.asyncio
async def test_sync_plugin_negative():

    fn = get_analysis("double")

    result = await fn({"value": -3})

    assert result == -6


@pytest.mark.asyncio
async def test_async_plugin_nonzero():

    fn = get_analysis("fit_gaussian")

    result = await fn({"seconds": 0.1})

    assert result == "done"


@pytest.mark.asyncio
async def test_invalid_analysis_name():

    with pytest.raises(KeyError):
        get_analysis("nonexistent")
