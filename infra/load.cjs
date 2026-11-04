// Sonda limitada de infraestrutura; não representa carga acadêmica completa.
const {performance} = require('node:perf_hooks');

async function main() {
  const [origin, countArg = '100', concurrencyArg = '4'] = process.argv.slice(2);
  const url = new URL(origin);
  if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password || url.search || url.hash || url.pathname !== '/')
    throw new Error('Informe somente a origem HTTP(S), sem credenciais, caminho ou query.');
  const count = Number(countArg), concurrency = Number(concurrencyArg);
  if (!Number.isInteger(count) || count < 1 || count > 10000 ||
      !Number.isInteger(concurrency) || concurrency < 1 || concurrency > 128)
    throw new Error('Limites: 1..10000 requisições; 1..128 clientes simultâneos.');
  let issued = 0;
  const timings = [], statuses = {};
  const started = performance.now();
  await Promise.all(Array.from({length: Math.min(concurrency, count)}, async () => {
    while (issued < count) {
      issued++;
      const start = performance.now();
      let status = 'network_error';
      try {
        const response = await fetch(new URL('/healthz', url), {signal: AbortSignal.timeout(10000), redirect: 'error'});
        status = String(response.status);
        // Não acumular conteúdo das respostas em memória.
        await response.body?.cancel();
      } catch { /* Contabilizado separadamente; sem retries que ampliem carga. */ }
      statuses[status] = (statuses[status] || 0) + 1;
      timings.push(performance.now() - start);
    }
  }));
  const elapsed = performance.now() - started;
  timings.sort((a, b) => a - b);
  const percentile = p => Math.round(timings[Math.ceil(timings.length * p) - 1]);
  console.log(JSON.stringify({origin: url.origin, count, concurrency, statuses,
    requests_per_second: +(count / (elapsed / 1000)).toFixed(2), p50_ms: percentile(.5),
    p95_ms: percentile(.95), p99_ms: percentile(.99)}, null, 2));
  if (statuses['200'] !== count) process.exitCode = 1;
}
main().catch(error => {console.error(error.message); process.exitCode = 1;});
