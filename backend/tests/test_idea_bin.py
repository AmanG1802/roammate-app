import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.idea_bin import idea_bin_service

@pytest.mark.asyncio
async def test_ingest_from_text_success():
    mock_db = AsyncMock()
    trip_id = 1
    text = "Colosseum, Pantheon"
    
    # Mock google_maps_service.find_place
    from app.services.idea_bin import google_maps_service
    google_maps_service.find_place = AsyncMock(side_effect=[
        {"name": "Colosseum", "place_id": "c1", "geometry": {"location": {"lat": 1, "lng": 1}}},
        {"name": "Pantheon", "place_id": "p1", "geometry": {"location": {"lat": 2, "lng": 2}}}
    ])
    
    items = await idea_bin_service.ingest_from_text(mock_db, trip_id, text)
    
    assert len(items) == 2
    assert items[0].title == "Colosseum"
    assert items[1].title == "Pantheon"
    assert mock_db.add.call_count == 2
    assert mock_db.commit.called

@pytest.mark.asyncio
async def test_ingest_from_text_empty():
    mock_db = AsyncMock()
    items = await idea_bin_service.ingest_from_text(mock_db, 1, "")
    assert len(items) == 0
    assert not mock_db.commit.called
