# Backend (FastAPI, to come)

Implements the endpoints listed at the bottom of `../design/api/types.ts` and returns exactly those shapes (the fixtures in `../design/api/fixtures/` are the reference responses). The frontend switches over by setting `VITE_USE_FIXTURES=false`; in dev it proxies `/api` to `http://localhost:8000`.
