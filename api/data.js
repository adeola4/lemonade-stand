// Vercel serverless function: /api/data
// Handles GET (read) and POST (write) to Google Sheets "LMS Data"
//
// Query params:
//   sheet=Missions|Loops|V1Loops|Deals|Pipeline|Staff   (required for GET)
//   action=list|get|create|update|delete                (required for POST)
//
// POST body (JSON):
//   { "sheet": "Missions", "action": "create", "row": {...} }
//   { "sheet": "Missions", "action": "update", "id": "m-123", "updates": {...} }
//   { "sheet": "Missions", "action": "delete", "id": "m-123" }

const SHEET_ID = '1JpnmKeIj3cKNPtiOjhH4tVSgdnU9p1_xuAIEyUBSOng';
const API_KEY = process.env.GOOGLE_SHEETS_API_KEY; // Vercel env var

// Google Sheets REST API (no SDK needed in serverless)
async function sheetsFetch(path, options = {}) {
  const url = `https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}${path}`;
  const headers = { 'Content-Type': 'application/json' };
  if (API_KEY) headers['Authorization'] = `Bearer ${API_KEY}`;
  const res = await fetch(url, { ...options, headers });
  return res.json();
}

// Read all rows from a sheet tab
async function readSheet(sheet) {
  const data = await sheetsFetch(`/values/${sheet}!A1:Z1000`);
  const rows = data.values || [];
  if (rows.length < 2) return [];
  const headers = rows[0];
  return rows.slice(1).map(row => {
    const obj = {};
    headers.forEach((h, i) => { obj[h] = row[i] || ''; });
    return obj;
  });
}

// Get a single row by ID
async function getRow(sheet, id) {
  const rows = await readSheet(sheet);
  return rows.find(r => r.id === id) || null;
}

// Append a new row
async function appendRow(sheet, row) {
  const values = Object.values(row);
  const data = await sheetsFetch(`/values/${sheet}!A1:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS`, {
    method: 'POST',
    body: JSON.stringify({ values: [values] })
  });
  return data;
}

// Update a row (find by ID, write back)
async function updateRow(sheet, id, updates) {
  const data = await sheetsFetch(`/values/${sheet}!A1:Z1000`);
  const rows = data.values || [];
  if (rows.length < 2) return { error: 'No data' };
  const headers = rows[0];
  const rowIndex = rows.findIndex((r, i) => i > 0 && r[0] === id);
  if (rowIndex === -1) return { error: 'Row not found' };
  
  const updatedRow = rows[rowIndex].map((cell, i) => {
    const key = headers[i];
    return updates[key] !== undefined ? String(updates[key]) : cell;
  });
  
  await sheetsFetch(`/values/${sheet}!A${rowIndex + 1}:Z${rowIndex + 1}?valueInputOption=RAW`, {
    method: 'PUT',
    body: JSON.stringify({ values: [updatedRow] })
  });
  return { ok: true };
}

// Delete a row (find by ID, clear or remove)
async function deleteRow(sheet, id) {
  const data = await sheetsFetch(`/values/${sheet}!A1:Z1000`);
  const rows = data.values || [];
  if (rows.length < 2) return { error: 'No data' };
  const rowIndex = rows.findIndex((r, i) => i > 0 && r[0] === id);
  if (rowIndex === -1) return { error: 'Row not found' };
  
  // Clear the row (safer than deleting, preserves structure)
  const emptyRow = rows[rowIndex].map(() => '');
  await sheetsFetch(`/values/${sheet}!A${rowIndex + 1}:Z${rowIndex + 1}?valueInputOption=RAW`, {
    method: 'PUT',
    body: JSON.stringify({ values: [emptyRow] })
  });
  return { ok: true };
}

export default async function handler(req, res) {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }
  
  try {
    if (req.method === 'GET') {
      const { sheet } = req.query;
      if (!sheet) return res.status(400).json({ error: 'Missing sheet param' });
      const rows = await readSheet(sheet);
      return res.status(200).json({ ok: true, data: rows });
    }
    
    if (req.method === 'POST') {
      const { sheet, action, id, row, updates } = req.body;
      if (!sheet || !action) return res.status(400).json({ error: 'Missing sheet or action' });
      
      switch (action) {
        case 'list': {
          const rows = await readSheet(sheet);
          return res.status(200).json({ ok: true, data: rows });
        }
        case 'get': {
          const row = await getRow(sheet, id);
          return res.status(200).json({ ok: true, data: row });
        }
        case 'create': {
          const result = await appendRow(sheet, row);
          return res.status(200).json({ ok: true, data: result });
        }
        case 'update': {
          const result = await updateRow(sheet, id, updates);
          return res.status(200).json({ ok: true, data: result });
        }
        case 'delete': {
          const result = await deleteRow(sheet, id);
          return res.status(200).json({ ok: true, data: result });
        }
        default:
          return res.status(400).json({ error: `Unknown action: ${action}` });
      }
    }
    
    return res.status(405).json({ error: 'Method not allowed' });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
}
