# Registro de falhas (F22)

| data | etapa | sintoma | causa | correção | commit |
|---|---|---|---|---|---|
| 2026-11-23 | C4 | yt-dlp avisa "n challenge solving failed" no YouTube; formatos podem faltar | yt-dlp 2026.10 exige runtime JS + resolvedor EJS; só deno vem habilitado | pip yt-dlp-ejs 0.8.0 + --js-runtimes node (Node já instalado) | 0c3ea34 |
