# Regras de negócio implementadas

Mapa de cada regra do enunciado para o ponto do código que a garante e o teste que a cobre.

## Webhook e ingestão

| Regra                                                        | Onde vive                                           | Teste                                                    |
| ------------------------------------------------------------ | --------------------------------------------------- | -------------------------------------------------------- |
| Só `MESSAGE_RECEIVED` é processado; demais eventos → 200 OK   | `conversations/views.py::message_webhook`           | `test_evento_nao_suportado_e_ignorado`                    |
| Idempotência por `message_id`                                 | `Message.external_id` (`unique`) + `get_or_create`  | `test_mensagem_duplicada_e_ignorada_silenciosamente`      |
| Webhook não executa IA; valida, persiste e enfileira          | `conversations/services/ingestion.py`               | `test_mensagem_recebida_e_persistida_e_enfileirada`       |
| Telefone identifica uma conversa única                        | `Conversation.user_phone` (`unique`)                | `test_mensagens_do_mesmo_telefone_compartilham_a_conversa`|
| Payload fora do contrato é rejeitado                          | `conversations/payloads.py`                         | `test_payload_incompleto_retorna_400`                     |

Respostas do endpoint:

- aceita → `{"status": "accepted", "message_id": ...}`
- evento não suportado ou duplicata → `{"status": "ignored", "message_id": ...}`
- `MESSAGE_RECEIVED` malformado → `400` com `{"error": ...}`

## Debounce

| Regra                                                           | Onde vive                              | Teste                                                    |
| ---------------------------------------------------------------- | -------------------------------------- | -------------------------------------------------------- |
| Mensagens em até 10s geram um único processamento                | `conversations/tasks.py`               | `test_debounce_descarta_execucao_de_mensagem_superada`    |
| A rajada inteira vira uma resposta só                            | histórico completo enviado ao modelo   | `test_ultima_mensagem_da_rajada_gera_um_unico_processamento` |

O intervalo é configurável por `MESSAGE_DEBOUNCE_SECONDS` (padrão 10).

## Busca de imóveis

| Regra                                                              | Onde vive                                        | Teste                                                  |
| ------------------------------------------------------------------- | ------------------------------------------------ | ------------------------------------------------------ |
| Código dispensa os demais filtros                                   | `PropertyFilters.missing_required`               | `test_codigo_dispensa_os_demais_filtros`               |
| Sem código: exige tipo de negócio + bairro + ao menos um preço      | `PropertyFilters.missing_required`               | `test_busca_sem_filtros_obrigatorios_nao_retorna_imoveis` |
| Tipo de negócio inválido conta como ausente                         | `PropertyFilters.missing_required`               | `test_tipo_de_negocio_invalido_conta_como_ausente`     |
| Piso, teto ou faixa de preço                                        | `properties/services/search.py::_apply_filters`  | `test_faixa_de_preco_e_bairro_sem_acento`              |
| Quartos é opcional                                                  | `properties/services/search.py::_apply_filters`  | coberto por `properties/tests/test_search.py`          |
| Máximo de 2 imóveis por busca                                       | `settings.MAX_PROPERTIES_PER_SEARCH`             | `test_limite_de_dois_imoveis_por_busca`                |
| Nunca repetir imóvel já recomendado na conversa                     | `exclude_codes` + `ToolContext`                  | `test_imoveis_ja_recomendados_sao_excluidos`, `test_busca_valida_registra_recomendacoes_no_contexto` |
| Consulta por código escapa da exclusão (não é recomendação nova)    | `properties/services/search.py`                  | `test_busca_por_codigo_ignora_a_exclusao_de_recomendados` |
| Bairro casa sem depender de caixa ou acento                         | `Property.neighborhood_key` + `common.text`      | `test_faixa_de_preco_e_bairro_sem_acento`              |

A garantia dos filtros mínimos é **determinística**: `search_properties` levanta
`IncompleteFiltersError` antes de qualquer consulta ao banco. Não existe caminho no código em que o
modelo receba imóveis sem os filtros obrigatórios, independentemente do que ele decida chamar
(`test_busca_sem_filtros_minimos_nao_devolve_imoveis` verifica isso pela tool, e não pelo service).

## Assistente

| Regra                                                    | Onde vive                                     |
| --------------------------------------------------------- | --------------------------------------------- |
| Responder sempre em pt-BR                                 | `assistant/prompts.py`                        |
| Perguntar quando faltarem informações obrigatórias        | retorno `filtros_insuficientes` da tool       |
| Não inventar imóveis nem regras da imobiliária            | prompt + tools como única fonte de dados      |
| Responder FAQ apenas com o conteúdo da base               | `assistant/tools/faq.py`                      |
| Admitir que não sabe quando a base não cobre o assunto    | `resultados: []` + mensagem explícita         |
| Ciclo de tools não pode girar indefinidamente             | `OPENAI_MAX_TOOL_ITERATIONS`                  |
| Falha ou resposta vazia do modelo não deixa o cliente sem retorno | `FALLBACK_REPLY` em `assistant/runner.py` |

## Persistência da conversa

| Regra                                                       | Onde vive                                          |
| ------------------------------------------------------------ | -------------------------------------------------- |
| Resposta da IA é persistida (não é enviada a API externa)    | `conversations/services/replies.py`                |
| Toda recomendação é persistida                               | `Recommendation` + `bulk_create(ignore_conflicts)` |
| `last_message_at` reflete cliente e assistente               | `Conversation.register_activity`                   |
| Conversa nasce `active`                                      | `ConversationStatus.ACTIVE` como default           |
| Uma conversa pode ter múltiplas buscas                       | sem limite de chamadas por conversa                |

## API de histórico

`GET /api/conversations/{user_phone}/messages` devolve exatamente:

```json
{
  "user_phone": "+5581982860171",
  "properties_found": ["IMV-001", "C011"],
  "messages": [
    {"role": "customer", "content": "...", "timestamp": "2026-06-02T10:00:00Z"}
  ]
}
```

- ordem cronológica crescente, garantida por `Message.Meta.ordering = ("timestamp", "id")`;
- `properties_found` na ordem em que os imóveis foram recomendados;
- timestamps em UTC com sufixo `Z`, e não `+00:00`, para bater com o formato do enunciado;
- conversa inexistente → `404`.

Coberto por `test_historico_segue_o_contrato_e_a_ordem_cronologica`, que compara o JSON inteiro.
