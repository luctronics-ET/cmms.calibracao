from datetime import date
from pathlib import Path
from backend.importacao import processar_csv

FIXTURE = Path("tests/fixtures/amostra_inventario.csv").read_bytes()


def _proc():
    return processar_csv(FIXTURE)


def test_ignora_linha_vazia():
    res = _proc()
    # 5 linhas de dados úteis (a 6ª é vazia)
    assert res["totais"]["total_linhas"] == 5


def test_mapeia_campos_por_conteudo():
    linha = _proc()["linhas"][0]["dados"]
    assert linha["equipamento"] == "ANALISADOR DE ESPECTRO"
    assert linha["disciplina"] == "ELE"
    assert linha["sistema"] == "EXOCET"
    assert linha["organizacao_calibradora"] == "CMS"        # SITUAÇÃO -> org
    assert linha["flag_origem"] == "DESCALIBRADO"           # VALIDADE -> flag
    assert linha["data_validade"] == date(2025, 9, 13)      # PRÓXIMA -> validade
    assert linha["data_ultima_calibracao"] == date(2024, 9, 13)
    assert linha["ciclo_meses"] == 12
    assert str(linha["custo_estimado"]) == "3104.95"


def test_marca_value_gera_aviso():
    linha = next(l for l in _proc()["linhas"]
                 if l["dados"]["codigo_interno"] == "CMASM-IDM-T46-054")
    assert linha["dados"]["data_validade"] is None
    assert any(p["severidade"] == "aviso" for p in linha["problemas"])


def test_sem_serial_nao_eh_erro():
    linha = next(l for l in _proc()["linhas"]
                 if l["dados"]["codigo_interno"] == "MAN-EXO-MEC-001")
    assert all(p["severidade"] != "erro" for p in linha["problemas"])


def test_totais_somam():
    t = _proc()["totais"]
    assert t["validas"] + t["com_erro"] == t["total_linhas"]


def test_detecta_duplicatas():
    import csv
    import io
    from backend.importacao import _mapa_indices

    # reutiliza o cabeçalho real da fixture (pode conter quebras embutidas em campos)
    cabecalho = next(csv.reader(io.StringIO(FIXTURE.decode("utf-8-sig"))))
    indices = _mapa_indices(cabecalho)
    n_cols = len(cabecalho)

    def _linha():
        cols = [""] * n_cols
        cols[indices["disciplina"]] = "ELE"
        cols[indices["equipamento"]] = "MULTIMETRO"
        cols[indices["marca"]] = "FLUKE"
        cols[indices["modelo"]] = "87V"
        cols[indices["codigo_interno"]] = "DUP-001"
        cols[indices["serial"]] = "SN-9"
        return cols

    buf = io.StringIO()
    escritor = csv.writer(buf)
    escritor.writerow(cabecalho)
    escritor.writerow(_linha())
    escritor.writerow(_linha())
    csv_bytes = buf.getvalue().encode("utf-8")

    res = processar_csv(csv_bytes)
    linhas = res["linhas"]
    assert len(linhas) == 2
    for linha in linhas:
        dups = [p for p in linha["problemas"]
                if p["campo"] == "duplicata" and p["severidade"] == "aviso"]
        assert len(dups) == 1
