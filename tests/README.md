# Roammate Test Suite

This directory contains the structured test suite for the Roammate application.

## Structure

- `backend/`: Python unit tests using `pytest` and `pytest-asyncio`.
  - `test_ripple_engine.py`: Logic for itinerary shifting.
  - `test_idea_bin.py`: Logic for location ingestion.
- `frontend/`: React unit and component tests using `vitest` and `React Testing Library`.
  - `store.test.ts`: Zustand state management tests.
  - `IdeaBin.test.tsx`: Component interaction tests.
- `e2e/`: Placeholder for Playwright/Cypress end-to-end flows.

## Running Tests

### Backend
```bash
cd backend
pytest
```

### Frontend
```bash
cd frontend
npm test
```
