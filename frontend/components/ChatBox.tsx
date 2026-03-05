'use client';

import React, { useState } from 'react';

export default function ChatBox() {
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState('');

  async function ask() {
    const res = await fetch(process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8080/ask', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer user-demo-token',
      },
      body: JSON.stringify({ query, top_k: 3 }),
    });
    const payload = await res.json();
    setAnswer(payload.answer ?? payload.detail ?? 'No answer');
  }

  return (
    <section>
      <h2>Chat</h2>
      <textarea value={query} onChange={(e) => setQuery(e.target.value)} rows={4} style={{ width: '100%' }} />
      <button onClick={ask}>Ask</button>
      <pre>{answer}</pre>
    </section>
  );
}
