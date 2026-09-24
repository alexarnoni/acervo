# Spotify Analytics

Projeto de portfólio para vaga de Data Analyst júnior: transforma o histórico completo do
Spotify Extended Streaming History (2014-2026, ~413 mil eventos de reprodução) em um modelo
dimensional limpo, pronto para consumo no Power BI.

## Pergunta de negócio

**Como meu comportamento de escuta mudou ao longo de 12 anos?**

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

Coloque os arquivos `Streaming_History_Audio_*.json` do seu export do Spotify em
`data/raw/` (mantendo a subpasta `Spotify Extended Streaming History/` ou direto em
`data/raw/`, o pipeline busca recursivamente).

Rodar o pipeline do zero:

```bash
cd src
python pipeline.py
```

Isso gera em `data/processed/`:
- `fact_streams.csv`
- `dim_artist.csv`
- `dim_track.csv`
- `dim_date.csv`
- `data_quality_report.md`

Rodar os testes:

```bash
pytest tests/ -v
```

## Modelo de dados (esquema estrela)

| Tabela | Grão | Chave |
|---|---|---|
| `fact_streams` | 1 linha por evento de reprodução de música | `stream_id` |
| `dim_artist` | 1 linha por artista | `artist_id` |
| `dim_track` | 1 linha por (faixa, artista, álbum) | `track_id` |
| `dim_date` | 1 linha por dia, do primeiro ao último dia do histórico | `date_key` |

Podcasts e audiobooks são identificados e separados dos dados de música (não entram nas
tabelas fato/dimensão, já que o foco do projeto é catálogo musical).

## Montando o Power BI rápido

A pasta [`powerbi/`](powerbi/) tem tudo pronto pra colar, sem precisar clicar tabela por
tabela na importação:

- [`powerbi/m_queries.txt`](powerbi/m_queries.txt) — script Power Query M por tabela (Editor
  Avançado), já com os tipos de coluna certos
- [`powerbi/measures.dax`](powerbi/measures.dax) — todas as medidas DAX prontas
- [`powerbi/visuals_guide.md`](powerbi/visuals_guide.md) — quais visuais montar, em ordem de
  prioridade, pra contar a história do relatório

## Dashboard

_(placeholder — screenshot do Power BI Desktop a adicionar depois)_

## Relatório analítico

Ver [reports/README.md](reports/README.md) para a análise completa com storytelling,
principais insights e limitações dos dados.

## Estrutura do repositório

```
spotify-analytics/
├── data/
│   ├── raw/              # JSONs originais (gitignored)
│   └── processed/        # CSVs limpos + relatório de qualidade (gitignored)
├── src/
│   ├── ingest.py
│   ├── transform.py
│   ├── validate.py
│   └── pipeline.py
├── notebooks/
│   └── exploracao.ipynb
├── reports/
│   └── README.md
└── tests/
    └── test_transform.py
```

## O que não está incluso (fases futuras)

- Arquivo `.pbix` do Power BI (montado manualmente apontando para os CSVs)
- Modelos de machine learning ou detecção de anomalia avançada
- Deploy

## Dashboard web (spotify.alexarnoni.com)

Camada pública e somente leitura do portfólio: `frontend/` (Vanilla JS + Chart.js) → `backend/` (FastAPI) → PostgreSQL com o mesmo schema estrela gerado pelo pipeline.
O prompt de origem está em [`docs/prompt_spotify_site.md`](docs/prompt_spotify_site.md).

```
backend/    API FastAPI (só GET, CORS restrito, rate limit, cache)
frontend/   dashboard estático (config.js define a URL da API)
database/   setup_db.sql (schema) + load_data.py (carga dos CSVs)
nginx/      proxy local e exemplo de produção
```

### Rodar localmente

```bash
docker compose up -d --build
DATABASE_URL=postgresql://spotify:spotify@localhost:5433/spotify python database/load_data.py --truncate
```

Abra http://localhost:8081. O `load_data.py` lê `data/processed/*.csv` (gerados pelo pipeline), usa só as colunas do schema (IP e localização nunca entram) e descarta eventos duplicados do export.

Testes da API: `cd backend && pip install -r requirements-dev.txt && pytest`

### Deploy (Oracle VM + Cloudflare)

1. Na VM: clone o repo, `cp .env.example .env` e troque `POSTGRES_PASSWORD` e `CORS_ORIGINS`.
2. Copie `data/processed/*.csv` para a VM (não são versionados) e rode `docker compose up -d db api`, depois o `load_data.py`.
3. Nginx do host: use `nginx/production.conf.example` (proxy para `127.0.0.1:8000`) — em produção mapeie a porta da API no compose (`ports: ["127.0.0.1:8000:8000"]`).
4. Cloudflare DNS: registro do subdomínio da API apontando para o IP da VM (proxy ligado); libere 80/443 na Security List da OCI.
5. Cloudflare Pages: publique `frontend/` e edite `frontend/config.js` (`API_BASE`) com a URL da API. Aponte `spotify.alexarnoni.com` para o projeto Pages.
