# Registro de falhas (F22)

| data | etapa | sintoma | causa | correção | commit |
|---|---|---|---|---|---|
| 2026-11-23 | C4 | yt-dlp avisa "n challenge solving failed" no YouTube; formatos podem faltar | yt-dlp 2026.10 exige runtime JS + resolvedor EJS; só deno vem habilitado | pip yt-dlp-ejs 0.8.0 + --js-runtimes node (Node já instalado) | 0c3ea34 |
| 2026-11-24 | montagem com templates (A4) | prévia de canal com kit sem fontes.titulo (cofre) quebraria no _kit da montagem | montagem lia o template texto_tela do kit sempre, mesmo sem texto simples | kit do texto simples só é lido quando um segmento usa texto simples; validação marca pendência se o kit não o tiver | a70914c |
| 2026-11-24 | montagem com templates (A4) | na amostra, a fala atrasava ~3 s a partir do 2º segmento falado; citação fora de sincronia | narração montada no mesmo grafo do passe final (com o vídeo); com segmento sem narração (anullsrc), o ffmpeg desalinhava a faixa | narração vira narr.wav num comando à parte; passe final só mistura (C5/C6: vídeo idêntico, fala nos mesmos tempos) | a70914c |
