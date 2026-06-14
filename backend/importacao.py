"""Parser + validação dry-run do CSV legado. Não toca no banco."""
from __future__ import annotations
import csv
import io
from backend.parsing import (
    normalizar_cabecalho, parse_data, parse_moeda, parse_ciclo,
)

# cabeçalho normalizado -> campo do modelo
MAPA_COLUNAS = {
    "ele/mec": "disciplina",
    "equipamento": "equipamento",
    "marca": "marca",
    "modelo": "modelo",
    "range": "faixa",
    "unidade range": "unidade_faixa",
    "cod interno": "codigo_interno",
    "serial": "serial",
    "divisão": "sistema",
    "ciclo calibração": "ciclo_meses",
    "ultima calibração": "data_ultima_calibracao",
    "última calibração": "data_ultima_calibracao",
    "próxima calibração": "data_validade",
    "validade calibração": "flag_origem",
    "situação": "organizacao_calibradora",
    "local calibração": "local_calibracao",
    "custo estimado": "custo_estimado",
    "custo contrat (r$)": "custo_contratado",
    "certificado": "certificado_ref",
    "comentários": "observacoes",
}
CAMPOS_DATA = {"data_ultima_calibracao", "data_validade"}
CAMPOS_MOEDA = {"custo_estimado", "custo_contratado"}


def _decodificar(conteudo: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return conteudo.decode(enc)
        except UnicodeDecodeError:
            continue
    return conteudo.decode("utf-8", errors="replace")


def _mapa_indices(cabecalho: list[str]) -> dict[str, int]:
    """campo -> índice da coluna. Para campos repetidos (certificado), fica o 1º."""
    indices: dict[str, int] = {}
    for i, bruto in enumerate(cabecalho):
        campo = MAPA_COLUNAS.get(normalizar_cabecalho(bruto))
        if campo and campo not in indices:
            indices[campo] = i
    return indices


def processar_csv(conteudo: bytes) -> dict:
    texto = _decodificar(conteudo)
    leitor = list(csv.reader(io.StringIO(texto)))
    if not leitor:
        return {"totais": {"total_linhas": 0, "validas": 0, "com_aviso": 0, "com_erro": 0}, "linhas": []}

    indices = _mapa_indices(leitor[0])
    linhas_saida = []
    validas = com_aviso = com_erro = 0

    for numero, bruto in enumerate(leitor[1:], start=2):
        if not any(c.strip() for c in bruto):
            continue  # linha totalmente vazia

        dados: dict = {}
        problemas: list[dict] = []

        for campo, i in indices.items():
            valor = bruto[i].strip() if i < len(bruto) else ""
            if campo in CAMPOS_DATA:
                d, aviso = parse_data(valor)
                dados[campo] = d
                if aviso:
                    problemas.append({"severidade": "aviso", "campo": campo, "mensagem": aviso})
            elif campo in CAMPOS_MOEDA:
                dados[campo] = parse_moeda(valor)
            elif campo == "ciclo_meses":
                c = parse_ciclo(valor)
                if c is None:
                    dados[campo] = 12
                    problemas.append({"severidade": "aviso", "campo": campo,
                                      "mensagem": "ciclo ausente; assumido 12 meses"})
                else:
                    dados[campo] = c
            elif campo == "disciplina":
                v = valor.upper()
                dados[campo] = v if v in ("ELE", "MEC") else None
            else:
                dados[campo] = valor or None

        # validação de severidade
        if not dados.get("equipamento") and not dados.get("codigo_interno"):
            problemas.append({"severidade": "erro", "campo": "linha",
                              "mensagem": "linha sem equipamento e sem código interno"})

        # divergência flag x data
        flag = (dados.get("flag_origem") or "").upper()
        val = dados.get("data_validade")
        if flag.startswith("DESCAL") and val is not None:
            from datetime import date as _d  # comparação informativa apenas
            problemas.append({"severidade": "aviso", "campo": "flag_origem",
                              "mensagem": "marcado DESCALIBRADO mas possui data de validade"})

        tem_erro = any(p["severidade"] == "erro" for p in problemas)
        tem_aviso = any(p["severidade"] == "aviso" for p in problemas)
        if tem_erro:
            com_erro += 1
        else:
            validas += 1
            if tem_aviso:
                com_aviso += 1

        linhas_saida.append({"numero": numero, "dados": dados, "problemas": problemas})

    total = len(linhas_saida)
    return {
        "totais": {"total_linhas": total, "validas": validas,
                   "com_aviso": com_aviso, "com_erro": com_erro},
        "linhas": linhas_saida,
    }
