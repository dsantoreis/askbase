'use client';

import React, { useEffect, useState } from 'react';

export default function AdminPage() {
  const [stats, setStats] = useState<{ chunks_loaded: number; index_path: string } | null>(null);

  useEffect(() => {
    fetch(process.env.NEXT_PUBLIC_API_URL?.replace('/ask', '/admin/stats') ?? 'http://127.0.0.1:8080/admin/stats', {
      headers: { Authorization: 'Bearer admin-demo-token' },
    })
      .then((r) => r.json())
      .then(setStats)
      .catch(() => setStats(null));
  }, []);

  return (
    <div>
      <h2>Admin Panel</h2>
      <p>Auth + observability snapshot</p>
      <pre>{JSON.stringify(stats, null, 2)}</pre>
    </div>
  );
}
