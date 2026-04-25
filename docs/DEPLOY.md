# 🚀 Deploy LeakLab no GitHub Pages — Passo a Passo

Tempo total: **~10-15 minutos**. Não precisa ser dev. Resultado: link público pra você compartilhar com qualquer pessoa.

---

## ✅ O que já está pronto

Tudo na pasta `docs/`:
- `index.html` (3 MB) — app com dados de exemplo embutidos
- `leaklab-blank.html` — versão sem dados
- `manifest.json` + `icons/` — PWA installable
- `.nojekyll` — arquivo técnico que precisa estar lá

**Você só precisa subir essa pasta inteira pro GitHub.**

---

## Passo 1: Conta GitHub (se já tem, pula)

1. Vai em **https://github.com/signup**
2. Email + senha + usuário
3. Confirma email pelo link que chegar

> Username vai ser parte do link público. Sugestão: algo curto e memorável (ex: `davidson-poker`).

---

## Passo 2: Criar o repositório

1. Logado, clica em **https://github.com/new** (ou no `+` no canto superior direito → "New repository")

2. Preenche:
   - **Repository name:** `leaklab` (sugerido — vira parte da URL)
   - **Description:** `Quiz GTO de pôquer MTT — treino de ranges interativo`
   - **Public** ✅ (importante — privado não funciona com Pages grátis)
   - **NÃO** marque "Initialize with README" (vamos subir o nosso)

3. Clica **"Create repository"** (verde, embaixo)

---

## Passo 3: Subir os arquivos (método web — sem Git)

Você ESTÁ na página do repo recém-criado. Vai ter algo tipo:
> `quick setup — if you've done this kind of thing before...`

1. Clica no link **"uploading an existing file"** (no meio da página, em texto azul)

   *URL direta:* `https://github.com/SEU-USUARIO/leaklab/upload/main`

2. **No seu computador**, abre a pasta:
   ```
   C:\Users\Davidson\Documents\Claude Code\poker-leak-finder\poker-leak-finder\docs
   ```

3. **Seleciona TUDO dentro de `docs/`** (Ctrl+A) e arrasta pra área de upload do GitHub:
   - `index.html`
   - `leaklab-blank.html`
   - `manifest.json`
   - `.nojekyll`
   - `DEPLOY.md` (esse arquivo)
   - `QUIZ_SPEC.md`
   - pasta `icons/` (com 3 arquivos SVG)

   ⚠️ **IMPORTANTE:** seleciona o CONTEÚDO de docs/, não a pasta docs em si. Os arquivos vão pra raiz do repo.

4. Aguarda upload terminar (barra de progresso embaixo)

5. **Commit changes** — caixinha embaixo:
   - Mensagem: `Initial deploy`
   - Selecione **"Commit directly to the main branch"**
   - Clica botão verde **"Commit changes"**

---

## Passo 4: Ativar GitHub Pages

1. No repo, clica na aba **"Settings"** (canto superior direito do repo, junto com Issues/Pull Requests)

   *URL direta:* `https://github.com/SEU-USUARIO/leaklab/settings`

2. Menu lateral esquerdo → **"Pages"**

   *URL direta:* `https://github.com/SEU-USUARIO/leaklab/settings/pages`

3. Em **"Build and deployment"**:
   - **Source:** `Deploy from a branch`
   - **Branch:** `main` (dropdown) · `/ (root)` (segundo dropdown)
   - Clica **Save**

4. **Aguarda 1-3 minutos.** Atualiza a página. Vai aparecer:
   > 🟢 *Your site is live at https://SEU-USUARIO.github.io/leaklab/*

---

## Passo 5: Testa!

Abre `https://SEU-USUARIO.github.io/leaklab/` no navegador.

✅ Deve mostrar a tela "🎯 LeakLab" com botão "▶ Começar Quiz"
✅ Clica → vai pro Quiz com mesa visual + ranges 80bb
✅ Joga 5 perguntas pra confirmar tudo funcionando

### Testa PWA install (celular)

1. Abre `https://SEU-USUARIO.github.io/leaklab/` no Chrome/Safari do celular
2. Menu (3 pontos) → **"Adicionar à tela inicial"**
3. Vai virar app no celular, ícone próprio, abre offline

---

## Passo 6: Compartilhar

Manda o link **`https://SEU-USUARIO.github.io/leaklab/`** pra:
- Grupos de WhatsApp de amigos jogadores
- Discord/Telegram de pôquer brasileiro
- Reddit r/poker (BR)
- Forum Brazilian Poker
- Stake/Backer

Sugestão de mensagem:
> "Fiz um quiz interativo de ranges GTO pra MTT. Mesa visual, atalhos de teclado, mobile-friendly. Sem cadastro nem nada. Topa testar?
>
> 🎯 https://SEU-USUARIO.github.io/leaklab/"

---

## 🔄 Atualizar depois

Quando você fizer mudanças locais (ou eu fizer):

### Web (mais simples)
1. Vai em `https://github.com/SEU-USUARIO/leaklab`
2. Clica em qualquer arquivo que mudou (ex: `index.html`)
3. Clica no ícone de lápis (✏️) "Edit this file"
4. Cola o conteúdo novo (gerado por `python src/build_app.py`)
5. Commit changes

### Git (se já usa)
```bash
git clone https://github.com/SEU-USUARIO/leaklab.git
cd leaklab
# faz mudanças, copia novos arquivos
git add .
git commit -m "update"
git push
```

GitHub Pages atualiza sozinho em 1-2 min após cada commit.

---

## 🐛 Problemas comuns

### "Site is live" mas dá 404
- Aguarda mais 5 min (DNS propagation)
- Confirma que `index.html` está na **raiz** do repo (não dentro de `docs/`)
- Settings → Pages → certifica que está `/ (root)` selecionado

### Ícones não aparecem
- Confirma que pasta `icons/` foi enviada com os 3 SVGs
- Manifest.json deve estar na raiz junto com index.html

### PWA não instala
- Precisa ser HTTPS (GitHub Pages já é)
- Manifest.json válido
- Service worker NÃO é obrigatório pro install (já roda)

### Range library vazia online
- Self-fix: app baixa ranges automaticamente do diretório de origem
- Workaround: clica em "↻ Recarregar do servidor" na aba Range Library

---

## 🎁 Alternativas ao GitHub Pages

### Netlify Drop (mais simples ainda — sem conta)
1. Vai em **https://app.netlify.com/drop**
2. Arrasta a pasta `docs/` inteira
3. Recebe URL aleatória (`xyz123.netlify.app`) na hora
4. Pode fazer login depois pra customizar URL

### Cloudflare Pages
1. Login com GitHub → conecta repo `leaklab`
2. Build settings: deixa default (publica `docs/`)
3. URL automática: `leaklab.pages.dev`

### Vercel
1. Login com GitHub → import repo
2. Framework: Other (estático)
3. Output directory: `docs`

---

## 🔒 Privacidade

- **Hand histories suas NÃO precisam ir pro GitHub.** Mantém localmente.
- O `index.html` deployado tem só **7 hands de exemplo** (anônimas).
- Quem quiser usar com dados próprios faz upload via "📊 Carregar Mãos" no app.

---

## ✅ Checklist final

Depois de seguir os passos, você deve ter:

- [ ] Repo GitHub público em `https://github.com/SEU-USUARIO/leaklab`
- [ ] Pages ativo em `https://SEU-USUARIO.github.io/leaklab/`
- [ ] App carrega corretamente
- [ ] Quiz funciona (jogou 5 perguntas)
- [ ] PWA instalou no celular (opcional)
- [ ] Compartilhou com pelo menos 1 amigo

🎉 **Pronto! Você publicou um app web grátis.**
