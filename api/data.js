// Vercel serverless function: /api/data
// Proxies to local data server via Hermes proxy (port 8645, tailnet-only)
// The proxy already handles auth (X-API-Key) and CORS.

const BACKEND_URL = 'https://agent-openclaw.tailae9a9f.ts.net';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-API-Key');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    const { sheet } = req.query;

    if (req.method === 'GET') {
      if (!sheet) return res.status(400).json({ error: 'Missing sheet param' });
      const backendRes = await fetch(`${BACKEND_URL}/data/${encodeURIComponent(sheet)}`, {
        headers: { 'X-API-Key': 'lms-default-key-2026' }
      });
      const json = await backendRes.json();
      return res.status(200).json(json);
    }

    if (req.method === 'POST') {
      const { action, id, row, updates } = req.body;
      if (!sheet || !action) return res.status(400).json({ error: 'Missing sheet or action' });

      const backendRes = await fetch(`${BACKEND_URL}/data/${encodeURIComponent(sheet)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': 'lms-default-key-2026' },
        body: JSON.stringify({ action, id, row, updates })
      });
      const json = await backendRes.json();
      return res.status(200).json(json);
    }

    return res.status(405).json({ error: 'Method not allowed' });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
}
