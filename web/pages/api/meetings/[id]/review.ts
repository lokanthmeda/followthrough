import type { NextApiRequest, NextApiResponse } from 'next';

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') return res.status(405).json({ error: 'Method not allowed' });
  const { id } = req.query;
  try {
    const response = await fetch(`${BACKEND_URL}/meetings/${id}/review`);
    const text = await response.text();
    let data: any = {};
    try {
      data = JSON.parse(text);
    } catch {
      data = { error: text || `HTTP ${response.status} from backend` };
    }
    if (!response.ok) {
      return res.status(response.status).json({
        error: data.detail || data.error || text || `Backend error (status ${response.status})`,
      });
    }
    res.status(response.status).json(data);
  } catch (error: any) {
    res.status(500).json({ error: error.message || 'Internal proxy error' });
  }
}
