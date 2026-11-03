# Busca de Tempos de Arrancada

Todos os tempos de arrancada publicados em [produpark.com.br](http://www.produpark.com.br/temposOnline), reunidos numa página só para cada piloto encontrar as próprias passadas sem ter que abrir evento por evento.

- **Página de busca:** `docs/index.html` (publicada pelo GitHub Pages)
- **Planilha:** `tempos_produpark.xlsx`, com todas as passadas, a melhor de cada piloto por evento e a lista de eventos

Na página dá para buscar por nome do piloto, número do carro ou modelo, e filtrar por ano, evento, categoria e fase (treino, classificação, mata-mata).

Os dados são os tempos extraoficiais que a própria Produpark publica no site dela. Esta página não é oficial e não tem ligação com a Produpark. Se algum tempo estiver errado, o site original é a referência.

## Atualizar os dados

É preciso ter Python 3 com `openpyxl` (`pip install openpyxl`).

No Windows, dê dois cliques em `atualizar.bat`. Ou rode na mão:

```
python scripts/scrape.py dados
python scripts/build.py dados
```

Depois copie `dados/dados.js` para `docs/` e `dados/tempos_produpark.xlsx` para a raiz. Para publicar, faça commit e push.

O `scrape.py` guarda as páginas baixadas em `dados/cache/`, então as próximas atualizações só baixam o que é novo. Se um evento estava ao vivo quando foi baixado, apague o `dados/cache/` para buscar esse evento de novo, completo.
