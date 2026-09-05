# Carga de imóveis

## O problema

Dois arquivos com imóveis diferentes precisam virar uma única tabela, sem duplicar em cargas
repetidas, e a Realmate pretende adicionar XML de parceiros e APIs REST de portais nos próximos
meses. O objetivo do desenho é que um formato novo seja uma classe nova, e não uma refatoração.

## Estrutura

```
src/properties/sources/
├── base.py       PropertyRecord, PropertySource, FilePropertySource
├── files.py      CsvPropertySource, JsonPropertySource
└── registry.py   SOURCES + build_sources()

src/properties/services/importer.py    import_properties()
src/properties/tasks.py                task agendada às 00:00 UTC
src/properties/management/commands/carregar_imoveis.py
```

`PropertySource` é o contrato: um método `fetch()` que produz `PropertyRecord` normalizados. O
importador não sabe se o registro veio de arquivo, de HTTP ou de uma fila; ele só recebe registros.

`FilePropertySource` é uma base intermediária para origens em arquivo. Ela já implementa a conversão
para `PropertyRecord`, o tratamento de linha inválida e a extração do código; cada formato concreto
só declara **como ler linhas** (`read_rows`) e **onde está o código** (`code_pattern`). É por isso
que `CsvPropertySource` e `JsonPropertySource` têm 8 linhas cada.

## A pegadinha do código do imóvel

O código não vem em coluna própria em nenhuma das duas origens. Ele está embutido no texto da
descrição, em formatos diferentes:

| Origem | Trecho da descrição      | Padrão                       |
| ------ | ------------------------ | ---------------------------- |
| CSV    | `... codigo:IMV-001`     | `codigo\s*:\s*(?P<code>...)` |
| JSON   | `... ref: C011`          | `ref\s*:\s*(?P<code>...)`    |

Cada origem declara o próprio `code_pattern`. Isso é deliberado: um regex único que aceitasse os dois
prefixos faria o formato de uma origem virar responsabilidade da outra, e a terceira origem (XML) já
nasceria acoplada às duas primeiras. Uma linha sem código é registrada em log e ignorada, porque a
carga não pode parar por causa de um registro ruim.

## Idempotência

`update_or_create` com `code` como chave. Rodar a carga N vezes produz sempre 20 imóveis; a partir da
segunda execução tudo é `updated`. A escolha entre *atualizar* e *ignorar* foi por atualizar: o
arquivo é a fonte da verdade e mudanças de preço precisam refletir no banco.

O resultado volta como `ImportSummary(created, updated, skipped)`, somável entre origens. É o que o
command imprime e o que a task devolve para observabilidade.

## Agendamento

`CELERY_BEAT_SCHEDULE` em `src/config/settings.py`, com `crontab(hour=0, minute=0)` e
`CELERY_TIMEZONE = "UTC"`. Não usamos `django-celery-beat`: ele existe para permitir editar
agendamentos em runtime pelo admin, e aqui o schedule é fixo e único, então seria uma dependência e
uma tabela a mais sem uso.

## Como adicionar um formato novo

Exemplo de XML de parceiro. Um arquivo novo:

```python
# src/properties/sources/partner_xml.py
class PartnerXmlSource(FilePropertySource):
    name: ClassVar[str] = "partner_xml"
    code_pattern: ClassVar[re.Pattern[str]] = re.compile(r"cod\s*:\s*(?P<code>[\w-]+)", re.IGNORECASE)

    def read_rows(self) -> Iterator[Mapping[str, object]]:
        for element in ElementTree.parse(self.path).findall("imovel"):
            yield {child.tag: child.text for child in element}
```

E uma linha no `registry.py`:

```python
SOURCES = {
    ...,
    PartnerXmlSource.name: lambda: PartnerXmlSource(settings.DATA_DIR / "parceiro.xml"),
}
```

Para uma **API REST**, a origem herda direto de `PropertySource` (não de `FilePropertySource`) e
implementa `fetch()` paginando o endpoint. Nada muda no importador, na task, no command ou no modelo.

O `carregar_imoveis` aceita `--source` (repetível, validado contra o registry), então é possível
recarregar apenas uma origem sem tocar nas outras.
