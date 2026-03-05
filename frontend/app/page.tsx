import Link from 'next/link';

export default function Home() {
  return (
    <div>
      <h1>Enterprise RAG Platform</h1>
      <p>Chat ops + admin controls for retrieval pipelines.</p>
      <ul>
        <li><Link href="/chat">Chat Console</Link></li>
        <li><Link href="/admin">Admin Panel</Link></li>
      </ul>
    </div>
  );
}
