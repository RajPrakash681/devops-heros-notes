const express = require('express');
const os = require('os');

const app = express();
const PORT = process.env.PORT || 3000;

app.get('/', (_req, res) => {
  res.send(`<!doctype html>
<meta charset="utf-8">
<title>Hello from Node.js</title>
<style>
  body { margin:0; height:100vh; display:grid; place-items:center;
         font:16px/1.5 system-ui, sans-serif; background:#0b1120; color:#e2e8f0; }
  .card { text-align:center; }
  h1 { margin:0 0 .4rem; font-size:2rem; color:#68d391; }
  code { background:#1e293b; padding:.15rem .4rem; border-radius:4px; }
</style>
<div class="card">
  <h1>Hello World from Node.js</h1>
  <p>Express ${require('express/package.json').version} on Node ${process.version}</p>
  <p>Served from container <code>${os.hostname()}</code></p>
  <p>Raj Prakash &mdash; DevOps Heros session 6&ndash;7</p>
</div>`);
});

app.listen(PORT, '0.0.0.0', () => console.log(`nodejs-app listening on ${PORT}`));
