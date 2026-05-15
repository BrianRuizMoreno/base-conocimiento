---
name: testing-patterns
description: Testing strategy for the RAG system. pytest for backend, Vitest for frontend. Unit tests for parsers, integration tests for RAG pipeline, end-to-end for upload→chat flow.
---

# Testing Patterns

## Backend (pytest)
```
backend/tests/
├── conftest.py           # Fixtures: db, client, auth
├── unit/
│   ├── test_parsers.py   # PDF, DOCX, JSON, XML parsing
│   ├── test_chunking.py  # Chunk size, overlap
│   └── test_security.py  # PIN hash, API key validation
├── integration/
│   ├── test_upload.py    # Upload → parse → embed flow
│   ├── test_chat.py      # Chat endpoint with mocked LLM
│   └── test_rag.py       # Full retrieval pipeline
└── e2e/
    └── test_full_flow.py # Upload doc → ask question → verify answer
```

### conftest.py
```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.main import app
from app.db.database import Base, get_db

TEST_DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/test_db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)

@pytest.fixture
async def db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine) as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def client(db):
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)
```

### Example: Parser Test
```python
def test_pdf_parser():
    pages = parse_pdf("tests/fixtures/sample.pdf")
    assert len(pages) > 0
    assert "expected text" in pages[0]

def test_json_streaming():
    chunks = list(parse_json_streaming("tests/fixtures/large.json"))
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)
```

## Frontend (Vitest)
```
frontend/src/
├── __tests__/
│   ├── components/
│   │   ├── MetricCard.test.tsx
│   │   └── DarkModeToggle.test.tsx
│   ├── hooks/
│   │   └── useApi.test.ts
│   └── pages/
│       └── AdminDashboard.test.tsx
```

### Example: Component Test
```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import DarkModeToggle from '@/components/admin/DarkModeToggle';

describe('DarkModeToggle', () => {
  it('toggles dark mode on click', () => {
    render(<DarkModeToggle />);
    const button = screen.getByRole('button');
    fireEvent.click(button);
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });
});
```

## vitest.config.ts
```ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/__tests__/setup.ts']
  },
  resolve: {
    alias: {
      '@': './src'
    }
  }
});
```
