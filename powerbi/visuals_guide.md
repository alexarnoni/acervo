# Guia rápido de visuais (para montar o dashboard sob pressão de tempo)

Ordem sugerida, do mais rápido ao mais elaborado. Os 3 primeiros já contam a história
principal do relatório em `reports/README.md`.

## 1. Cartões de KPI (topo da página)

Três cartões simples com as medidas:
- `[Total Horas]`
- `[Total Plays]`
- `[Artistas Distintos]`

## 2. Gráfico de colunas empilhadas — a virada de artista dominante

- Visual: **Gráfico de Colunas Empilhadas**
- Eixo X: `dim_date[year]`
- Legenda: `dim_artist[artist_name]`
- Valores: `[Total Horas]`
- Filtro visual: Top N = 5 artistas por `[Total Horas]` (Filtros > Filtro de Top N sobre
  `artist_name`, por `Total Horas`)

Mostra Arctic Monkeys dominando 2014-2024 e Twenty One Pilots assumindo em 2025.

## 3. Gráfico de linha — diversidade de artistas por ano

- Visual: **Gráfico de Linhas**
- Eixo X: `dim_date[year]`
- Valores: `[Artistas Distintos]`

Mostra os dois picos (2015-2016 e 2024-2026) descritos no relatório.

## 4. Tabela — top 10 artistas

- Visual: **Tabela**
- Colunas: `artist_name`, `[Total Horas]`, `[Total Plays]`
- Ordenar por `[Total Horas]` decrescente, Top N = 10

## 5. (Opcional, se sobrar tempo) Skip Rate por ano

- Visual: **Gráfico de Linhas**
- Eixo X: `dim_date[year]`
- Valores: `[Skip Rate]`
- Adicionar uma caixa de texto acima explicando que o campo não é confiável antes de 2022
  (ver limitação no relatório) — ou filtrar o visual só para 2022+ usando `[Skip Rate 2022+]`.

## Formatação rápida

- Tema: Formatar > Temas > escolher um tema escuro ou o padrão do Power BI (não gaste tempo
  customizando cores agora).
- Título da página: "Spotify Analytics — 12 anos de escuta (2014-2026)".
- Adicionar um cartão de texto com a fonte dos dados: "Fonte: Spotify Extended Streaming
  History, export pessoal".
