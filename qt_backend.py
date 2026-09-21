import pandas as pd
from io import BytesIO


def read_sped_file(file_path):
    """Read a SPED file path and return (corpo_sped, assinatura) lists."""
    with open(file_path, "rb") as f:
        conteudo = f.read().decode("latin-1", errors="replace")
    linhas = conteudo.splitlines()
    return _split_body_signature(linhas)


def _split_body_signature(linhas):
    """Split SPED content into body and signature (block 9 at end)."""
    assinatura_idx = None
    for i, linha in enumerate(linhas):
        if linha.startswith("|9") and len(linha.split("|")) > 2 and linha.split("|")[1].startswith("9"):
            is_last_block = True
            for next_line in linhas[i + 1 :]:
                if next_line.startswith("|") and not next_line.startswith("|9"):
                    is_last_block = False
                    break
            if is_last_block:
                assinatura_idx = i
                break

    if assinatura_idx is not None:
        corpo_sped = linhas[:assinatura_idx]
        assinatura = linhas[assinatura_idx:]
    else:
        corpo_sped = linhas
        assinatura = []
    return corpo_sped, assinatura


def load_sped_layout(file_path="sped_descricao/sped_descritivo.txt"):
    """Load SPED layout into {REGISTRO: {CAMPO: index_base_1}}."""
    layout = {}
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or not line.startswith("|"):
                continue
            parts = line.split("|")
            if len(parts) < 4:
                continue
            registro = parts[1]
            campos = parts[2:-2]
            if not registro:
                continue
            layout[registro] = {}
            for i, nome_campo in enumerate(campos):
                if nome_campo:
                    layout[registro][nome_campo] = i + 2
    return layout


def build_excel_bytes(corpo_sped, sped_layout):
    """Build Excel bytes with one sheet per registro."""
    dataframes_por_registro = {}
    if sped_layout:
        for linha in corpo_sped:
            if not linha.startswith("|"):
                continue
            partes = linha.split("|")
            if len(partes) < 2:
                continue
            registro = partes[1]
            if registro in sped_layout:
                if registro not in dataframes_por_registro:
                    dataframes_por_registro[registro] = []
                linha_dict = {}
                campos_layout = sped_layout[registro]
                for nome_campo, indice_layout in campos_layout.items():
                    if indice_layout < len(partes):
                        linha_dict[nome_campo] = partes[indice_layout]
                    else:
                        linha_dict[nome_campo] = None
                dataframes_por_registro[registro].append(linha_dict)

    if not dataframes_por_registro:
        return None

    output_excel = BytesIO()
    with pd.ExcelWriter(output_excel, engine="xlsxwriter") as writer:
        for registro, lista_linhas in dataframes_por_registro.items():
            if not lista_linhas:
                continue
            col_order = list(sped_layout[registro].keys())
            df_reg = pd.DataFrame(lista_linhas, columns=col_order)
            sheet_name = registro.replace(":", "_").replace("/", "_")[:31]
            df_reg.to_excel(writer, index=False, sheet_name=sheet_name)
    return output_excel.getvalue()


def build_csv_bytes(corpo_sped):
    """Build CSV bytes using semicolon separator, based on current body."""
    linhas_modificadas = []
    for linha in corpo_sped:
        linha_limpa = linha
        if linha.startswith("|"):
            linha_limpa = linha_limpa[1:]
        if linha.endswith("|"):
            linha_limpa = linha_limpa[:-1]
        linhas_modificadas.append(linha_limpa.replace("|", ";"))
    csv_content = "\n".join(linhas_modificadas)
    return csv_content.encode("latin-1", errors="replace")


def safe_float_conversion(value_str):
    """Convert a string to float with comma handling."""
    if not value_str:
        return 0.0
    try:
        return float(value_str.replace(".", "", value_str.count(".") - 1).replace(",", ".").strip())
    except (ValueError, TypeError):
        return 0.0


def build_summary(corpo_sped, sped_layout):
    """Return summary dataframes and metrics, mirroring Streamlit logic."""
    registros_interesse = {
        "C100": ["IND_OPER", "VL_DOC", "VL_BC_ICMS", "VL_ICMS"],
        "C170": ["CFOP", "VL_ITEM", "VL_BC_ICMS", "VL_ICMS"],
        "D100": ["IND_OPER", "VL_DOC", "VL_BC_ICMS", "VL_ICMS", "CFOP"],
    }

    dados_resumo = []
    for idx, linha in enumerate(corpo_sped):
        if not linha.startswith("|"):
            continue
        partes = linha.split("|")
        if len(partes) < 2:
            continue
        registro = partes[1]
        if registro in registros_interesse:
            linha_data = {"REG": registro, "LINHA_ORIGINAL": idx + 1}
            campos_layout_registro = sped_layout.get(registro, {})
            for nome_campo in registros_interesse[registro]:
                indice = campos_layout_registro.get(nome_campo)
                valor = 0.0
                valor_str = ""
                if indice and indice < len(partes):
                    valor_raw = partes[indice]
                    if nome_campo.startswith("VL_") or nome_campo.startswith("ALIQ_"):
                        valor = safe_float_conversion(valor_raw)
                    else:
                        valor_str = valor_raw.strip()
                    linha_data[nome_campo] = valor if nome_campo.startswith("VL_") else valor_str
                else:
                    linha_data[nome_campo] = valor if nome_campo.startswith("VL_") else valor_str
            dados_resumo.append(linha_data)

    if not dados_resumo:
        return None

    df_resumo = pd.DataFrame(dados_resumo)
    total_bc_icms = df_resumo["VL_BC_ICMS"].sum()
    total_icms = df_resumo["VL_ICMS"].sum()
    total_linhas = len(df_resumo)

    resumo_cfop = None
    if "CFOP" in df_resumo.columns:
        df_resumo["CFOP"] = df_resumo["CFOP"].fillna("N/A")
        resumo_cfop = (
            df_resumo.groupby("CFOP")
            .agg(
                Contagem=("CFOP", "size"),
                Total_BC_ICMS=("VL_BC_ICMS", "sum"),
                Total_ICMS=("VL_ICMS", "sum"),
            )
            .reset_index()
            .sort_values(by="Contagem", ascending=False)
        )

    resumo_tipo_op = None
    if "IND_OPER" in df_resumo.columns:
        df_resumo["Tipo_Operacao"] = df_resumo["IND_OPER"].apply(
            lambda x: "Entrada" if x == "0" else ("Saida" if x == "1" else "Outro")
        )
        resumo_tipo_op = (
            df_resumo.groupby("Tipo_Operacao")
            .agg(
                Contagem=("Tipo_Operacao", "size"),
                Total_BC_ICMS=("VL_BC_ICMS", "sum"),
                Total_ICMS=("VL_ICMS", "sum"),
            )
            .reset_index()
        )
    elif "CFOP" in df_resumo.columns:
        def classificar_cfop(cfop):
            if isinstance(cfop, str) and len(cfop) >= 1:
                primeiro_digito = cfop[0]
                if primeiro_digito in ["1", "2", "3"]:
                    return "Entrada (CFOP)"
                if primeiro_digito in ["5", "6", "7"]:
                    return "Saida (CFOP)"
            return "Outro"

        df_resumo["Tipo_Operacao"] = df_resumo["CFOP"].apply(classificar_cfop)
        resumo_tipo_op = (
            df_resumo.groupby("Tipo_Operacao")
            .agg(
                Contagem=("Tipo_Operacao", "size"),
                Total_BC_ICMS=("VL_BC_ICMS", "sum"),
                Total_ICMS=("VL_ICMS", "sum"),
            )
            .reset_index()
        )

    return {
        "df_resumo": df_resumo,
        "total_bc_icms": total_bc_icms,
        "total_icms": total_icms,
        "total_linhas": total_linhas,
        "resumo_cfop": resumo_cfop,
        "resumo_tipo_op": resumo_tipo_op,
    }


def filter_lines(corpo_sped, registro_escolhido, filtros_ativos, filtro_geral):
    """Filter lines for a registro with field and general filters."""
    linhas_filtradas = []
    for idx, linha in enumerate(corpo_sped):
        if not linha.startswith(f"|{registro_escolhido}|"):
            continue
        partes = linha.split("|")
        match_all = True
        for indice_campo, valor_filtro in filtros_ativos.items():
            if not (indice_campo < len(partes) and valor_filtro in partes[indice_campo]):
                match_all = False
                break
        if match_all and filtro_geral:
            if filtro_geral not in linha:
                match_all = False
        if match_all:
            linhas_filtradas.append((idx, linha))
    return linhas_filtradas


def apply_field_change(corpo_sped, registro, indice_campo, novo_valor, indices_para_alterar):
    """Apply a field change to selected indices."""
    linhas_modificadas_count = 0
    novo_corpo_sped = list(corpo_sped)
    linhas_alteradas_preview = []
    erros_alteracao = []

    for idx_original in indices_para_alterar:
        if idx_original >= len(novo_corpo_sped):
            erros_alteracao.append(
                f"Indice {idx_original + 1} invalido (maior que tamanho do arquivo)."
            )
            continue
        linha_original = novo_corpo_sped[idx_original]
        if not linha_original.startswith(f"|{registro}|"):
            erros_alteracao.append(
                f"Linha {idx_original + 1} nao parece ser do registro {registro}."
            )
            continue

        partes = linha_original.split("|")
        if indice_campo < len(partes):
            if partes[indice_campo] != novo_valor:
                partes[indice_campo] = novo_valor
                linha_modificada = "|".join(partes)
                novo_corpo_sped[idx_original] = linha_modificada
                linhas_modificadas_count += 1
                linhas_alteradas_preview.append(f"L{idx_original + 1}: {linha_modificada}")
        else:
            erros_alteracao.append(
                f"Linha {idx_original + 1} nao possui o campo na posicao esperada."
            )

    return novo_corpo_sped, linhas_modificadas_count, erros_alteracao, linhas_alteradas_preview


def build_full_content(corpo_sped, assinatura):
    """Serializa o SPED com CRLF e terminador após a última linha."""
    linhas = corpo_sped + assinatura
    if not linhas:
        return ""
    return "\r\n".join(linhas) + "\r\n"
