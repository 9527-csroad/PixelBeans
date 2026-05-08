# Vite dev server unreachable on Windows — IPv6-only binding

## Symptom
Browser shows `ERR_CONNECTION_REFUSED` / `chrome-error://chromewebdata` when accessing `http://localhost:5173/`, even though Vite logs show it's running.

## Root cause
On Windows with Node.js, `netstat` reveals Vite binds to `[::1]:5173` (IPv6 loopback only), not `127.0.0.1:5173` (IPv4). If `localhost` resolves to IPv4 first, the connection is refused.

## Fix
Always start Vite with `--host` to bind `0.0.0.0` (IPv4 + IPv6):

```bash
cd web && npm run dev -- --host
```

## Diagnose command
```bash
netstat -ano | findstr ":5173"
```
- `[::1]:5173` → IPv6 only (broken for IPv4 clients) → need `--host`
- `0.0.0.0:5173` or `127.0.0.1:5173` → OK
