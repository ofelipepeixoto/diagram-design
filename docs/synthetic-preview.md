# Prévia estática restrita

Exemplo sintético para documentação, sem dados de clientes, modelo ou serviço.
Usa a paleta do diagram-design (Cathryn Lavery, MIT); licença e autoria upstream
permanecem intactas. Não representa integração implantada.

`python scripts/safe_preview.py docs/synthetic-evidence-flow.svg /tmp/evidence-preview.html`

O comando nunca faz requests e recusa sobrescrever input/output existente.
Aceita somente SVG UTF-8 até 64 KiB, 256 elementos, profundidade 12, formas/texto
simples e atributos numéricos/cores explícitos. Recusa scripts, eventos, CSS,
imagens, links, href, use, namespaces diferentes, DTD e processing instructions.
O HTML resultante inclui CSP default-src 'none'. É um subconjunto deliberado;
arquivos normais do exportador com CSS/defs podem ser recusados. Não é um
sanitizador universal nem promessa de proteção contra falhas do navegador.
Use um navegador atualizado em ambiente isolado; não relaxe o gate para abrir
HTML arbitrário. `export_svg.py --system-fonts` continua apenas removendo fontes
externas, sem substituir este gate.

Teste: `python scripts/test-safe-preview.py`. Acessibilidade: título, descrição,
alto contraste e legenda textual; revisão por leitor de tela e renderização
visual continuam gates pendentes. Nenhum workflow foi habilitado.
