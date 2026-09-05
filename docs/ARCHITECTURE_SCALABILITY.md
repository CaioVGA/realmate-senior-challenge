# Limites conhecidos e caminhos de evolução

O que está implementado é proporcional ao problema descrito no enunciado. Este documento registra
onde cada decisão deixa de servir e qual seria o próximo passo, para que a evolução seja incremental
e não uma reescrita.

## 1. Debounce

**Hoje:** cada mensagem agenda uma task com `countdown=10`; a execução só prossegue se ainda for a
última mensagem do cliente. Isso é suficiente porque o enunciado garante que o cliente não envia nova
mensagem enquanto espera a resposta.

**Quando deixa de servir:** em produção real essa premissa cai. O cliente manda "ah, e com garagem"
enquanto a IA já está gerando a resposta, e duas execuções podem se sobrepor.

**Próximo passo:** lock por conversa (advisory lock no PostgreSQL ou `SET NX` no Redis) segurado
durante o processamento, com a mensagem que chega durante o lock reagendando a execução para logo
após a liberação. É uma mudança contida em `conversations/tasks.py`; nada mais precisa saber disso.

**Custo lateral:** o `countdown` mantém uma task ociosa por mensagem no broker. Com volume alto,
migrar para uma chave de debounce em Redis com uma única task por janela reduz a pressão na fila.

## 2. Filas

**Hoje:** uma fila única. Carga diária e resposta ao cliente disputam os mesmos workers.

**Quando deixa de servir:** assim que a carga passar a puxar milhares de imóveis de APIs de portais.
Uma carga longa passa a atrasar respostas de conversa, que são sensíveis a latência.

**Próximo passo:** duas filas (`realtime` e `batch`) com `task_routes` e workers dedicados. É
configuração em `settings.py`, sem mudança de código.

## 3. Busca de imóveis

**Hoje:** filtros exatos sobre colunas indexadas, com o bairro normalizado em `neighborhood_key`.
Índice composto `(transaction_type, neighborhood_key, price)`.

**Quando deixa de servir:**

- bairro escrito de forma que não bate por igualdade ("boa viajem", "b. viagem", "próximo à praia");
- filtros por características que hoje só existem em texto livre na descrição (garagem, piscina,
  mobiliado, aceita pet);
- ordenação por relevância em vez de preço.

**Próximo passo em ordem de custo:**

1. Tabela `Neighborhood` com apelidos conhecidos, resolvendo o bairro antes da consulta. Cobre a
   maioria dos casos sem tocar na busca.
2. Colunas booleanas para as características mais pedidas, extraídas na carga pelos parsers (que já
   são o lugar certo para normalizar dados de origem).
3. Busca híbrida (`SearchVector` do PostgreSQL sobre a descrição) somada aos filtros estruturados.

Embeddings de imóveis só se justificam quando a busca por características livres virar o caminho
principal, e mesmo aí os filtros obrigatórios continuam determinísticos: eles restringem o conjunto
antes de qualquer ranqueamento semântico. **Essa garantia não pode ser terceirizada para o modelo em
nenhuma fase da evolução.**

## 4. FAQ

**Hoje:** 10 entradas em JSON, carregadas em memória com `lru_cache` e ranqueadas por sobreposição de
tokens.

**Quando deixa de servir:** a partir de algumas dezenas de entradas, ou quando as perguntas passarem
a ser parafraseadas sem compartilhar palavras com a base ("posso levar meu cachorro?" contra uma
entrada que fala em "animais de estimação"). A sobreposição de tokens erra nesse caso.

**Próximo passo:** mover o FAQ para uma tabela (permite edição pelo time de operações, versionamento
e auditoria) e, se a paráfrase virar problema recorrente, adicionar embeddings com `pgvector`. A
troca fica contida na tool: o contrato exposto ao modelo (`consultar_faq(pergunta)`) não muda.

Enquanto forem 10 entradas estáveis, subir um banco vetorial é custo de infraestrutura e de
manutenção sem retorno.

## 5. Chamadas à OpenAI

**Hoje:** chamada síncrona dentro da task, com timeout configurável e teto de iterações de tools.
Erro de rede faz a task falhar.

**Quando deixa de servir:** qualquer instabilidade do provedor vira mensagem não respondida.

**Próximo passo:**

- `autoretry_for` com backoff exponencial na task, e `max_retries` limitado para não reprocessar
  eternamente;
- mensagem de fallback persistida quando os retries se esgotam, para o cliente nunca ficar sem
  resposta (a constante `FALLBACK_REPLY` já existe para o caso de resposta vazia);
- histórico truncado por janela (últimas N mensagens ou N tokens) quando as conversas ficarem
  longas. Hoje o histórico completo é enviado, o que é adequado para conversas de atendimento mas
  cresce linearmente em custo.

## 6. Persistência e volume

**Hoje:** consultas por conversa usam `Index(conversation, timestamp)`; a API devolve o histórico
completo.

**Quando deixa de servir:** conversas longas ou clientes recorrentes fazem a resposta da API crescer
sem limite.

**Próximo passo:** paginação por cursor na API de histórico e arquivamento de conversas encerradas.
O campo `status` já existe justamente para permitir esse corte. Falta apenas a regra de negócio que
decide quando encerrar uma conversa (hoje não há uma, por não estar no escopo).

## 7. Operação

O que faltaria para colocar isso em produção, fora do escopo do desafio:

- autenticação/assinatura do webhook (o enunciado dispensa explicitamente);
- métricas de negócio: taxa de buscas bloqueadas por filtro insuficiente, imóveis recomendados por
  conversa, latência ponta a ponta;
- rastreio das chamadas ao modelo (prompt, tools chamadas, tokens) para auditar respostas ruins;
- `gunicorn`/`uvicorn` no lugar do `runserver`, que hoje vem do entrypoint fornecido no esqueleto.
