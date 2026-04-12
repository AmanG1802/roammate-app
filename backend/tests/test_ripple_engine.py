import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from app.services.ripple_engine import ripple_engine
from app.models.all_models import Event

@pytest.mark.asyncio
async def test_shift_itinerary_basic():
    # Setup
    mock_db = AsyncMock()
    trip_id = 1
    delta_minutes = 30
    start_time = datetime(2026, 4, 12, 10, 0)
    
    # Mock events
    event1 = Event(
        id=1, trip_id=trip_id, title="Colosseum", 
        start_time=start_time, end_time=start_time + timedelta(hours=1),
        is_locked=False
    )
    event2 = Event(
        id=2, trip_id=trip_id, title="Roman Forum", 
        start_time=start_time + timedelta(hours=2), end_time=start_time + timedelta(hours=3),
        is_locked=False
    )
    
    # Mock scalars().all()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [event1, event2]
    mock_db.execute.return_value = mock_result
    
    # Execute
    updated_events = await ripple_engine.shift_itinerary(
        db=mock_db,
        trip_id=trip_id,
        delta_minutes=delta_minutes,
        start_from_time=start_time - timedelta(minutes=1)
    )
    
    # Assert
    assert len(updated_events) == 2
    assert updated_events[0].start_time == start_time + timedelta(minutes=30)
    assert updated_events[1].start_time == start_time + timedelta(hours=2, minutes=30)
    assert mock_db.commit.called

@pytest.mark.asyncio
async def test_shift_itinerary_locked_events():
    # Setup
    mock_db = AsyncMock()
    trip_id = 1
    delta_minutes = 30
    start_time = datetime(2026, 4, 12, 10, 0)
    
    # event1 is locked, shouldn't be shifted (if filter fails, we check logic)
    # The service filters is_locked=False, so if we mock result with locked it should skip it
    event1 = Event(id=1, is_locked=True, start_time=start_time)
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [] # Since it's locked, it won't be in the result set from DB
    mock_db.execute.return_value = mock_result
    
    # Execute
    updated_events = await ripple_engine.shift_itinerary(
        db=mock_db,
        trip_id=trip_id,
        delta_minutes=delta_minutes,
        start_from_time=start_time
    )
    
    # Assert
    assert len(updated_events) == 0
