# Person 1 — Frontend Setup

## What you built
A full web app with:
- Dark-themed live map (Leaflet.js on dark CartoDB tiles)
- Sidebar showing all pothole reports in real time
- "Report Pothole" modal — GPS auto-detect, photo upload, description
- Severity colour-coded pins on the map (green → red)
- Live stats in the topbar (total, critical, fixed)
- Auto-refresh every 15 seconds

---

## How to run

1. Make sure Person 2's backend is running at http://localhost:5000
2. Just open index.html in your browser — no install needed!
   - Double-click the file, OR
   - Run: `python -m http.server 3000` in this folder, then open http://localhost:3000

That's it. No npm, no build step.

---

## How it connects to the backend

All API calls go to http://localhost:5000 (Person 2's Flask server).

| Action | API call |
|--------|----------|
| Load all reports | GET /reports |
| Submit new report | POST /report |
| Load stats (topbar) | GET /stats |

---

## Severity colour system
| Score | Colour | Meaning |
|-------|--------|---------|
| 1 | Green | Minor crack |
| 2 | Light green | Small pothole |
| 3 | Yellow | Medium pothole |
| 4 | Orange | Large / dangerous |
| 5 | Red | Critical — road destroyed |

---

## Demo tip
Before the presentation, seed 5–6 fake reports using Person 2's API
so the map looks populated. The sidebar and map update automatically.
