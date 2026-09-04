import React, { useState } from 'react';

const wrap = {
  margin: 0, height: '100vh', display: 'grid', placeItems: 'center',
  font: '16px/1.5 system-ui, sans-serif', background: '#0b1120', color: '#e2e8f0',
};
const btn = {
  marginTop: '.8rem', padding: '.45rem 1rem', border: '1px solid #4a5568',
  borderRadius: '6px', background: '#1e293b', color: '#e2e8f0', cursor: 'pointer',
};

export default function App() {
  // A little state, so the page proves React is really running and not just
  // static HTML that happens to say "React".
  const [clicks, setClicks] = useState(0);

  return (
    <div style={wrap}>
      <div style={{ textAlign: 'center' }}>
        <h1 style={{ margin: '0 0 .4rem', fontSize: '2rem', color: '#b794f4' }}>
          Hello World from React
        </h1>
        <p>Built with Vite, served as static files by nginx</p>
        <p>Raj Prakash &mdash; DevOps Heros session 6&ndash;7</p>
        <button style={btn} onClick={() => setClicks((c) => c + 1)}>
          clicked {clicks} {clicks === 1 ? 'time' : 'times'}
        </button>
      </div>
    </div>
  );
}
