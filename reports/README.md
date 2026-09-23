# Relatório: 12 anos de escuta no Spotify

## Pergunta de negócio

Como meu comportamento de escuta mudou entre 2014 e 2026? Existe um artista dominante ao
longo do tempo, ou a preferência migra? A diversidade do que eu escuto aumenta ou diminui?

## Metodologia

Os dados vêm do export Extended Streaming History do Spotify (~413 mil eventos brutos).
Foram separados registros de música, podcast e audiobook; eventos de música com menos de 1
segundo de reprodução (ruído de troca de faixa) foram descartados, assim como duplicatas
exatas. O resultado (~317 mil reproduções válidas) foi modelado em esquema estrela
(`fact_streams` + dimensões de artista, faixa e data) para consumo direto no Power BI.
Detalhes de contagens e checagens de qualidade estão em
[`data/processed/data_quality_report.md`](../data/processed/data_quality_report.md)
(gerado a cada execução do pipeline).

## Principais insights

### 1. Um artista domina quase a década inteira — até 2025

| Artista | Horas totais (2014-2026) | Plays totais |
|---|---:|---:|
| Arctic Monkeys | 1.755,6 | 48.076 |
| Twenty One Pilots | 412,8 | 8.242 |
| The Beatles | 187,7 | 7.733 |
| Avenged Sevenfold | 159,2 | 3.534 |
| Pink Floyd | 155,2 | 2.967 |

Arctic Monkeys foi o artista mais ouvido por horas em **todos os anos de 2014 a 2024**, com
pico em 2020 (280 horas). A partir de **2025**, Twenty One Pilots assume a liderança anual
(158 horas em 2025, 68 horas nos primeiros meses de 2026) — a primeira virada de artista
dominante em toda a série.

### 2. A diversidade de artistas tem dois picos claros: 2015-2016 e 2024-2026

| Período | Artistas distintos/ano |
|---|---:|
| 2014 | 548 |
| 2015-2016 | 971 – 1.076 |
| 2017-2023 (vale) | 692 – 851 |
| 2024-2026 | 1.186 – 1.417 |

Depois do pico inicial de 2015-2016, a diversidade cai e se estabiliza numa faixa mais baixa
entre 2017 e 2023 (o período de maior fidelidade ao Arctic Monkeys). A partir de 2024 a
diversidade dispara para o maior nível da série (1.417 artistas distintos em 2025) — coincide
com a virada de artista dominante do insight 1.

### 3. Período anômalo detectado: 17/07/2018

Ao inspecionar picos de volume de reprodução por dia, **17/07/2018** se destaca: 293
reproduções no dia (vs. mediana de ~30-40 em dias normais daquele mês), com duração média de
apenas 49 segundos por play e distribuídas entre mais de 30 artistas diferentes, sem nenhum
artista concentrando mais que 30 plays. O padrão é consistente com uma sessão de navegação/
shuffle rápido por múltiplos artistas, não escuta deliberada — um outlier isolado, não uma
mudança de comportamento sustentada.

### 4. A plataforma "windows" concentra o maior volume, mas mistura dispositivos

| Plataforma | Plays |
|---|---:|
| windows | 68.007 |
| ios | 33.577 |
| android (agregado, várias versões/aparelhos) | ~150.000+ |

O Android aparece fragmentado em dezenas de strings diferentes (uma por versão de
SO/aparelho), enquanto "windows" e "ios" vêm consolidados. Comparações diretas de plataforma
exigem normalizar essas strings antes de tirar conclusões sobre hábito por dispositivo.

### 5. A taxa de skip não é confiável antes de 2022

O campo `skipped` reporta **0% de skips em todos os meses entre 2017 e 2021** — não porque o
usuário nunca pulou uma faixa nesse período, mas porque o Spotify não populava esse campo de
forma consistente nos exports mais antigos. A taxa de skip só passa a ter variação real a
partir de 2022 (7,8%) e sobe para a faixa de 39-49% em 2023-2026. Qualquer análise de
"engajamento por skip" deve ser restrita ao período 2022+.

## Limitações dos dados

- **Taxa de skip histórica não confiável** (ver insight 5): o campo `skipped` está zerado
  entre 2017 e 2021 por limitação do próprio export do Spotify, não por comportamento real.
- **Plataforma "windows" e "ios" agregam múltiplos dispositivos** sob um único rótulo,
  enquanto Android é fragmentado por versão/aparelho — os totais por plataforma não são
  diretamente comparáveis sem normalização.
- **`ms_played` não implica intenção**: uma reprodução de poucos segundos pode ser navegação
  em shuffle (ver insight 3), não necessariamente desgosto pela faixa.
- **Podcasts e audiobooks foram excluídos** do escopo de catálogo musical (3.041 eventos de
  podcast identificados, 0 de audiobook neste export) — o projeto foca em música.
- **Um registro totalmente vazio** (sem faixa, episódio ou audiobook) foi descartado
  silenciosamente na consolidação; não afeta as métricas de música.

## Próximos passos

- Montar o dashboard Power BI a partir dos CSVs em `data/processed/` (fora do escopo desta
  fase, feito manualmente).
- Investigar a virada Arctic Monkeys → Twenty One Pilots com uma linha do tempo mensal
  (não só anual) para identificar o mês exato de transição.
- Segunda fase: detecção de anomalias mais sistemática (não apenas o outlier pontual de
  17/07/2018) e possivelmente um modelo simples de recomendação sobre o próprio histórico.
