# TechPulse Standard — Scale & Security

## Production architecture
Users -> DNS -> CDN/WAF/DDoS protection -> cached static frontend -> static origin.

GitHub Actions -> RSS/Atom -> validation -> normalization -> deduplication -> ranking -> news.json.

Normal visitors should never call RSS sources directly.

## 10M+ traffic
The static, cache-first design is the correct foundation for high traffic because assets and news.json can be served from edge cache.

Do not claim GitHub Pages alone guarantees 10M users. Put a CDN/WAF in front of the public domain and load-test the public CDN endpoint. For sustained high volume, use an edge/static origin designed for the expected load.

## Security
- No API keys or secrets in browser files.
- Treat RSS content as untrusted.
- Escape dynamic content before HTML insertion.
- Keep the public site read-only.
- Preserve the last-known-good dataset if collection fails.
- Use least-privilege GitHub Actions.
- Pin production Actions to immutable commit SHAs.
- Enable dependency and secret scanning.
- Apply security headers at the CDN/edge.
- Monitor feed failures, deployments, origin errors and cache health.
- Maintain rollback and incident-response procedures.

No public system can honestly guarantee immunity from zero-days, provider outages, DNS failures, compromised accounts or every future attack.

Note: _headers is an edge-host template. Apply headers at the production CDN/edge; GitHub Pages does not generally treat _headers as a generic response-header file.
