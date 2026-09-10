# Deploy no Streamlit Community Cloud

Guia rápido para publicar o dashboard no Streamlit Community Cloud (gratuito).

## Pré-requisitos

- Repo `devLeandroCoelho/careercompass-br` **público** no GitHub
- Arquivo `requirements.txt` na raiz (já existe — só deps do dashboard)
- Arquivo `.streamlit/config.toml` (tema + config mínima — já existe)

## Passo a passo

### 1. Criar conta

1. Acesse **[share.streamlit.io](https://share.streamlit.io)**
2. Clique em **"Sign up"** → **"Continue with GitHub"**
3. Autorize o OAuth com a conta `devLeandroCoelho`

### 2. Criar o app

1. Na dashboard, clique em **"New app"**
2. Em **"Repository"**, selecione:
   - **Repo:** `devLeandroCoelho/careercompass-br`
   - **Branch:** `main`
   - **Main file path:** `src/dashboard/app.py`
3. Clique em **"Advanced settings"** → veja a seção abaixo
4. Clique em **"Deploy"**

> O primeiro deploy leva ~2-3 minutos. A URL pública será algo como
> `https://careercompass-br.streamlit.app` (nome gerado pelo Streamlit).

### 3. Secrets (opcional)

Este dashboard **não precisa de secrets** — os dados mock são gerados
em runtime e o DuckDB não está no cloud. Se no futuro houver necessidade
(ex: API key externa), adicione em **Advanced settings → Secrets**:

```toml
# Exemplo (NÃO necessário agora)
API_KEY = "sk-xxx"
```

### 4. Atualizações automáticas

A cada **push na branch `main`**, o Streamlit Cloud **re-deploya
automaticamente**. Basta fazer merge do PR e o app atualiza sozinho.

### 5. Logs e gerenciamento

1. Acesse **[share.streamlit.io](https://share.streamlit.io)**
2. Clique no app **CareerCompass BR**
3. Clique em **"Manage app"** (canto inferior esquerdo)
4. Lá você encontra:
   - **Logs** — erros de runtime, tracebacks
   - **Reboot** — reiniciar o app
   - **Delete** — remover o app

### 6. URL pública

Depois do deploy, a URL será:
```
https://<nome-do-repo>.streamlit.app
```
Exemplo: `https://careercompass-br.streamlit.app`

Para usar domínio próprio, veja a docs do Streamlit (requer plano pago ou CNAME).

## Arquivos relevantes

| Arquivo | Função |
|---------|--------|
| `requirements.txt` | Deps do dashboard (streamlit, plotly, pandas, duckdb, numpy) |
| `.streamlit/config.toml` | Tema, server headless, analytics |
| `src/dashboard/app.py` | Entry point do dashboard |

## Troubleshooting

| Erro | Causa | Solução |
|------|-------|---------|
| `ModuleNotFoundError: No module named 'src'` | `app.py` não adicionou `_root` ao path | Verificar `sys.path.insert` no `app.py` |
| `ModuleNotFoundError: No module named 'duckdb'` | `requirements.txt` ausente ou incompleto | Confirmar que `duckdb>=1.1` está no `requirements.txt` |
| `FileNotFoundError: warehouse.duckdb` | Esperado no cloud — não há DuckDB | O dashboard faz fallback para dados mock automaticamente |
| Build timeout | deps pesadas demais | Pinar versões exatas em `requirements.txt` |
