# InfraScan – Part 1 Frontend
Setup: `npm install` then `npm run dev` (http://localhost:5173). Demo login: demo@infrascan.test / demo123; choose a role to see that role's dashboard and menu.
Backend: copy `.env.example` to `.env` and set `VITE_API_BASE_URL`. All calls go through `src/services/api.js`; mock data is in `mockData.js` / `mockApi.js`.
Endpoint paths in api.js are proposals (align with Part 3). AI result shape: `sampleAnalysis()` in mockData.js (align with Part 2).
The damage map uses Leaflet + OpenStreetMap tiles and needs internet access.
