# Acervo

Projeto de dados de ponta a ponta sobre 12 anos do meu próprio histórico de escuta musical
(2014-2026, cerca de 413 mil eventos brutos do Spotify Extended Streaming History): limpeza e
validação em Python, modelagem em esquema estrela, relatório em Power BI e um dashboard público
que conta como o gosto mudou ao longo do tempo.

**Ao vivo:** https://musica.alexarnoni.com

- **Pipeline (Python + pandas):** separa podcasts, remove ruído e duplicados, retira IP e localização e valida chaves e faixas de data, com testes automatizados.
- **Modelo estrela:** `fact_streams` e `dim_artist`, `dim_track`, `dim_date`, prontos para Power BI (queries M e medidas DAX incluídas).
- **Qualidade de dados:** o campo de skip do export vem vazio em 2017-2021, então a métrica é derivada do evento de encerramento; escutas de terceiros são removidas por janelas de data.
- **Dashboard:** narrativa em cinco capítulos gerada a partir dos dados, feita em JavaScript puro com Chart.js e publicada de forma estática, sem servidor.
- **API (opcional):** PostgreSQL + FastAPI somente leitura, para rodar localmente com Docker Compose.

Ideias e próximos passos estão em [`ROADMAP.md`](ROADMAP.md).

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

### Escutas de terceiros

A conta foi emprestada a outras pessoas em alguns períodos (dez/2018, jun-jul/2018, fev/2019). Esses plays são removidos no pipeline por `drop_borrowed_listening` em `src/transform.py` (768 plays, ~37 h), só para os artistas listados e dentro de cada janela de datas (`BORROWED_ACCOUNT_WINDOWS`).

Para não depender de memória, `src/anomalies.py` sugere candidatos: artistas com mais da metade dos plays numa janela de 21 dias. A lista é revisada à mão, porque uma rajada também pode ser um álbum novo que virou obsessão.

### Skip

O campo `skipped` do export só vem preenchido em alguns períodos (0% em 2017–2021), então o site define skip como o play encerrado no botão avançar (`reason_end = 'fwdbtn'`), que existe em todos os anos.

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

## Dashboard web (musica.alexarnoni.com)

Camada pública e somente leitura do portfólio: `frontend/` (Vanilla JS + Chart.js) → `backend/` (FastAPI) → PostgreSQL com o mesmo schema estrela gerado pelo pipeline.

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

### Publicar (site estático, sem VM)

O histórico é fixo (até 21/09/2026), então o site publicado não precisa de servidor: `database/export_static.py` roda as mesmas queries da API e grava `frontend/data/*.json`, e o `frontend/config.js` está em `DATA_MODE = "static"`.

```bash
# atualizar os dados (só se reprocessar o histórico): banco carregado + export
DATABASE_URL=postgresql://spotify:spotify@localhost:5433/spotify python database/export_static.py
```

1. Faça push do repo (os JSONs de `frontend/data/` são versionados; os CSVs não).
2. Cloudflare Pages: conecte o repo `acervo`, sem build, diretório de saída `frontend`.
3. Domínio customizado do projeto Pages: `musica.alexarnoni.com` (o DNS é criado pelo próprio Pages).

Para usar a API ao vivo em vez dos JSONs, ponha `DATA_MODE = "api"` no `config.js` e siga o deploy abaixo.

### Deploy com API ao vivo (opcional: Oracle VM + Cloudflare)

1. Na VM: clone o repo, `cp .env.example .env` e troque `POSTGRES_PASSWORD` e `CORS_ORIGINS`.
2. Copie `data/processed/*.csv` para a VM (não são versionados) e rode `docker compose up -d db api`, depois o `load_data.py`.
3. Nginx do host: use `nginx/production.conf.example` (proxy para `127.0.0.1:$API_PORT` (padrão 8010; confira se está livre com `ss -tlnp`)); ajuste a porta no arquivo se mudar `API_PORT`.
4. Cloudflare DNS: registro do subdomínio da API apontando para o IP da VM (proxy ligado); libere 80/443 na Security List da OCI.
5. Cloudflare Pages: publique `frontend/` e edite `frontend/config.js` (`API_BASE`) com a URL da API. Aponte `musica.alexarnoni.com` para o projeto Pages.
