import json
from pathlib import Path

from properties.sources import CsvPropertySource, JsonPropertySource

CSV_CONTENT = """tipo_negocio,preco,quartos,bairro,endereco,descricao
aluguel,2500,2,Boa Viagem,"Rua dos Navegantes, 150","Apartamento com varanda. codigo:IMV-001"
venda,850000,4,Casa Forte,"Rua do Futuro, 512","Casa em condominio. codigo:IMV-002"
aluguel,1800,1,Gracas,"Rua das Gracas, 87","Studio mobiliado sem identificacao"
"""


def test_csv_source_extrai_codigo_da_descricao(tmp_path: Path) -> None:
    path = tmp_path / "imoveis.csv"
    path.write_text(CSV_CONTENT, encoding="utf-8")

    records = list(CsvPropertySource(path).fetch())

    assert [record.code for record in records] == ["IMV-001", "IMV-002"]
    assert records[0].transaction_type == "aluguel"
    assert records[0].neighborhood == "Boa Viagem"
    assert int(records[0].price) == 2500
    assert records[0].bedrooms == 2


def test_json_source_usa_padrao_de_codigo_proprio(tmp_path: Path) -> None:
    path = tmp_path / "imoveis_resumo.json"
    path.write_text(
        json.dumps(
            [
                {
                    "tipo_negocio": "aluguel",
                    "preco": 2200,
                    "quartos": 2,
                    "bairro": "Espinheiro",
                    "endereco": "Rua do Espinheiro, 340",
                    "descricao": "Apartamento com 2 quartos. ref: C011",
                }
            ]
        ),
        encoding="utf-8",
    )

    records = list(JsonPropertySource(path).fetch())

    assert [record.code for record in records] == ["C011"]


def test_linha_sem_codigo_e_ignorada_sem_interromper_a_carga(tmp_path: Path) -> None:
    path = tmp_path / "imoveis.csv"
    path.write_text(CSV_CONTENT, encoding="utf-8")

    assert len(list(CsvPropertySource(path).fetch())) == 2
