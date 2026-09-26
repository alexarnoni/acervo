# Roadmap

Ideias para o Acervo, separadas em o que está no plano e o que ficou de fora por ora.

## No plano (fase atual)

- [x] Detecção automática de anomalias (períodos de escuta atípica, como conta emprestada)
- [ ] Idade da música que eu ouço (ano de lançamento via MusicBrainz)
- [x] Sobrevivência de artistas (Kaplan-Meier): quanto tempo um artista descoberto continua sendo ouvido
- [x] Redescobertas / nostalgia: faixas que voltaram depois de mais de um ano parado
- [x] Eras automáticas: clustering dos meses pela mistura de artistas
- [x] Calendário de escuta, dia a dia (estilo GitHub)

## Ideias guardadas para depois

### Análises
- **Sessões de escuta:** agrupar plays por intervalos de mais de 30 min; duração média e sessões por dia.
- **Álbum inteiro ou faixa solta:** inferir pelas faixas em sequência.
- **Mudança de horário ao longo dos anos:** virei mais coruja?
- **Diversidade por entropia/Gini:** medir concentração, além da contagem de artistas.
- **Rede de artistas:** quais artistas aparecem na mesma sessão (grafo de co-escuta); liga com o projeto recomendador-playlists.
- **Faixas cravadas e faixas puladas:** as que nunca pulo vs. as que toco e sempre pulo.
- **Sazonalidade:** dezembro vs. julho; fim de semana vs. dia útil.

### Site
- **Seletor de ano** (cards, heatmap e rankings filtrados por ano) e comparador de dois anos.
- **Versão em inglês (pt/en):** o projeto Encore já é bilíngue.
- **Clicar num artista** e ver a linha do tempo de horas por ano.
- **Imagem de capa (og:image)** para o link no LinkedIn e no WhatsApp.
- **Busca** de artista ou música.
- **"Neste dia":** o que eu ouvia neste dia em cada ano anterior.
- **Dias de maratona:** os 16 dias com mais de 10 h, com contexto.
- **Gráfico de plataformas/aparelhos** (a partir de 2023 o campo vem em outro formato; precisa tratar).

### Engenharia
- **CI no GitHub Actions** rodando os testes, com selo no README.
- **Testes de dados** no pipeline (chaves órfãs, faixas de valores).
- **Dicionário de dados e diagrama do modelo (ER).**
- **Capturas do Power BI** no README.
