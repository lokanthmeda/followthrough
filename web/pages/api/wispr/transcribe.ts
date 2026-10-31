import type { NextApiRequest, NextApiResponse } from 'next';
import { IncomingForm } from 'formidable';
import fs from 'fs';

export const config = {
  api: { bodyParser: false },
};

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const form = new IncomingForm({ multiples: false });
    const [fields, files] = await new Promise<[any, any]>((resolve, reject) => {
      form.parse(req, (err: any, fields: any, files: any) => {
        if (err) reject(err);
        else resolve([fields, files]);
      });
    });

    if (!files.audio) {
      return res.status(400).json({ error: 'No audio file provided' });
    }

    const file = Array.isArray(files.audio) ? files.audio[0] : files.audio;
    const buffer = fs.readFileSync(file.filepath);

    const formData = new FormData();
    const audioBlob = new Blob([buffer], { type: file.mimetype || 'audio/wav' });
    formData.append('audio', audioBlob, 'recording.wav');
    formData.append('file', audioBlob, 'recording.wav');

    const response = await fetch(`${BACKEND_URL}/wispr/transcribe`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${process.env.WHISPER_API_KEY || ''}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return res.status(response.status).json(errorData);
    }

    const data = await response.json();

    // Cleanup temp file
    try { fs.unlinkSync(file.filepath); } catch { /* ignore */ }

    res.status(200).json(data);
  } catch (error: any) {
    res.status(500).json({ error: error.message || 'Transcription failed' });
  }
}