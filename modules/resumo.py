import streamlit as st
import pandas as pd
from utils import load_sped_layout # Importar load_sped_layout

# --- Funções Auxiliares (Específicas para Resumo) ---

def safe_float_conversion(value_str):
    """Tenta converter uma string para float, tratando vírgula e erros."""
    if not value_str:
        return 0.0
    try:
        # Substitui vírgula por ponto e remove espaços
        return float(value_str.replace('.', '', value_str.count('.') -1).replace(',', '.').strip())
    except (ValueError, TypeError):
        return 0.0 # Retorna 0 se a conversão falhar

def get_field_index(layout, registro, field_name):
    """Obtém o índice (base 1) de um campo no layout, tratando ausência."""
    if layout and registro in layout and field_name in layout[registro]:
        return layout[registro][field_name]
    return None # Retorna None se o campo/registro não existir no layout

# --- Função Principal do Resumo ---

def generate_summary(corpo_sped, assinatura):
    """Gera e exibe um resumo dos dados do SPED."""
    st.subheader("📊 Gerar Resumo do SPED")

    if not corpo_sped:
        st.info("Carregue um arquivo SPED para gerar o resumo.")
        return

    sped_layout = load_sped_layout()
    if not sped_layout:
        st.error("Layout SPED não carregado. Não é possível gerar resumo.")
        return

    # --- Coleta de Dados --- #
    # Lista para armazenar dicionários, cada um representando uma linha relevante
    dados_resumo = []
    print("[DEBUG][Resumo] Iniciando coleta de dados para resumo...")

    # Registros e campos de interesse (pode ser expandido)
    registros_interesse = {
        "C100": ["IND_OPER", "VL_DOC", "VL_BC_ICMS", "VL_ICMS"], # Documento Fiscal (Mercadorias)
        "C170": ["CFOP", "VL_ITEM", "VL_BC_ICMS", "VL_ICMS"],    # Itens do Documento (Mercadorias)
        "D100": ["IND_OPER", "VL_DOC", "VL_BC_ICMS", "VL_ICMS", "CFOP"], # Documento Fiscal (Serviços Transporte)
        # Adicionar outros registros conforme necessário (ex: C500 Energia, D500 Comunicação)
    }

    for idx, linha in enumerate(corpo_sped):
        if not linha.startswith('|'):
            continue

        partes = linha.split('|')
        if len(partes) < 2:
            continue

        registro = partes[1]

        if registro in registros_interesse:
            # Log a cada 1000 linhas processadas
            if idx % 1000 == 0:
                 print(f"[DEBUG][Resumo] Processando linha {idx+1} (Registro: {registro})")

            linha_data = {"REG": registro, "LINHA_ORIGINAL": idx + 1}
            campos_layout_registro = sped_layout.get(registro, {})

            for nome_campo in registros_interesse[registro]:
                indice = campos_layout_registro.get(nome_campo)
                valor = 0.0 # Default para campos numéricos
                valor_str = "" # Default para strings (CFOP, IND_OPER)

                if indice and indice < len(partes):
                    valor_raw = partes[indice]
                    # Tenta converter para float se for campo de valor/base
                    if nome_campo.startswith("VL_") or nome_campo.startswith("ALIQ_"):
                        valor = safe_float_conversion(valor_raw)
                    else:
                        valor_str = valor_raw.strip()
                    linha_data[nome_campo] = valor if nome_campo.startswith("VL_") else valor_str
                else:
                    # Campo não encontrado na linha ou no layout
                    linha_data[nome_campo] = valor if nome_campo.startswith("VL_") else valor_str
                    # print(f"[DEBUG][Resumo] Campo {nome_campo} não encontrado ou índice inválido na linha {idx+1} (Reg: {registro})")

            dados_resumo.append(linha_data)

    print(f"[DEBUG][Resumo] Coleta concluída. {len(dados_resumo)} linhas de dados relevantes encontradas.")

    if not dados_resumo:
        st.warning("Nenhum dado relevante para resumo encontrado nos registros de interesse (C100, C170, D100). Verifique o conteúdo do SPED.")
        return

    # --- Processamento com Pandas --- #
    try:
        df_resumo = pd.DataFrame(dados_resumo)
        print(f"[DEBUG][Resumo] DataFrame criado com {len(df_resumo)} linhas e colunas: {df_resumo.columns.tolist()}")

        # --- Cálculos dos Resumos --- #
        st.markdown("**Resumo Geral:**")
        col1, col2, col3 = st.columns(3)

        # Exemplo: Total Base de Cálculo ICMS (somando C100, C170, D100)
        # Cuidado: Somar C100 e C170 pode duplicar valores se ambos estiverem presentes.
        #          Idealmente, escolheríamos um ou outro, ou faríamos uma lógica mais complexa.
        #          Vamos somar tudo por enquanto para demonstração.
        total_bc_icms = df_resumo['VL_BC_ICMS'].sum()
        col1.metric("Total Base ICMS (Soma C100/C170/D100)", f"{total_bc_icms:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

        # Total Valor ICMS
        total_icms = df_resumo['VL_ICMS'].sum()
        col2.metric("Total Valor ICMS (Soma C100/C170/D100)", f"{total_icms:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

        # Total Documentos/Itens processados
        total_linhas = len(df_resumo)
        col3.metric("Total Linhas Relevantes Processadas", f"{total_linhas}")

        st.markdown("---")

        # --- Resumo por CFOP --- #
        st.markdown("**Resumo por CFOP:**")
        # Precisamos garantir que a coluna CFOP exista (pode vir de C170 ou D100)
        if 'CFOP' in df_resumo.columns:
            # Agrupar por CFOP e calcular totais e contagem
            # Preenche NaNs em CFOP (se houver) para evitar erros no groupby
            df_resumo['CFOP'] = df_resumo['CFOP'].fillna('N/A')
            resumo_cfop = df_resumo.groupby('CFOP').agg(
                Contagem=('CFOP', 'size'),
                Total_BC_ICMS=('VL_BC_ICMS', 'sum'),
                Total_ICMS=('VL_ICMS', 'sum'),
                # Adicionar mais agregações se necessário (ex: soma de VL_ITEM do C170)
            ).reset_index().sort_values(by="Contagem", ascending=False)

            st.dataframe(resumo_cfop, use_container_width=True)
        else:
            st.info("Coluna 'CFOP' não encontrada nos dados coletados para gerar resumo por CFOP.")

        # --- Resumo Entradas x Saídas (Baseado no CFOP ou IND_OPER) --- #
        st.markdown("---")
        st.markdown("**Resumo Entradas x Saídas (Simplificado):**")
        # Tentativa 1: Usar IND_OPER (0 = Entrada, 1 = Saída) - Presente em C100, D100
        if 'IND_OPER' in df_resumo.columns:
             df_resumo['Tipo_Operacao'] = df_resumo['IND_OPER'].apply(lambda x: 'Entrada' if x == '0' else ('Saída' if x == '1' else 'Outro'))
             resumo_tipo_op = df_resumo.groupby('Tipo_Operacao').agg(
                 Contagem=('Tipo_Operacao', 'size'),
                 Total_BC_ICMS=('VL_BC_ICMS', 'sum'),
                 Total_ICMS=('VL_ICMS', 'sum'),
             ).reset_index()
             st.dataframe(resumo_tipo_op, hide_index=True, use_container_width=True)
        # Tentativa 2: Se não houver IND_OPER, usar CFOP (1xxx, 2xxx, 3xxx = Entrada; 5xxx, 6xxx, 7xxx = Saída)
        elif 'CFOP' in df_resumo.columns:
            def classificar_cfop(cfop):
                if isinstance(cfop, str) and len(cfop) >= 1:
                    primeiro_digito = cfop[0]
                    if primeiro_digito in ['1', '2', '3']:
                        return 'Entrada (por CFOP)'
                    elif primeiro_digito in ['5', '6', '7']:
                        return 'Saída (por CFOP)'
                return 'Outro/N/A'

            df_resumo['Tipo_Operacao'] = df_resumo['CFOP'].apply(classificar_cfop)
            resumo_tipo_op_cfop = df_resumo.groupby('Tipo_Operacao').agg(
                 Contagem=('Tipo_Operacao', 'size'),
                 Total_BC_ICMS=('VL_BC_ICMS', 'sum'),
                 Total_ICMS=('VL_ICMS', 'sum'),
             ).reset_index()
            st.dataframe(resumo_tipo_op_cfop, hide_index=True, use_container_width=True)
        else:
            st.info("Não foi possível determinar Entradas/Saídas (sem IND_OPER ou CFOP nos dados coletados).")


    except Exception as e:
        st.error(f"Ocorreu um erro ao processar os dados para o resumo: {e}")
        print(f"[DEBUG][Resumo] Erro durante processamento Pandas: {e}")
        # Opcional: Mostrar o DataFrame parcial para depuração, se ele foi criado
        # if 'df_resumo' in locals():
        #     st.expander("Dados parciais coletados (para depuração)").dataframe(df_resumo.head(50))

    # Limpar o placeholder de aviso
    # (Remover o st.warning inicial)

    # --- Lógica de Resumo (a ser implementada) ---
    # Exemplo: Contar linhas por tipo de registro
    # registro_counts = pd.Series([l.split('|')[1] for l in corpo_sped if l.startswith('|') and len(l.split('|')) > 1]).value_counts()
    # st.write("Contagem de Linhas por Registro:")
    # st.dataframe(registro_counts)

    # Exemplo: Totalizar valores (precisa identificar registro e campo correto)
    # total_icms_d100 = 0
    # for l in corpo_sped:
    #     if l.startswith("|D100|"):
    #         try:
    #             partes = l.split('|')
    #             valor_icms_str = partes[15].replace(',', '.') # Campo 15 = VL_ICMS, ajustar índice se necessário
    #             if valor_icms_str:
    #                 total_icms_d100 += float(valor_icms_str)
    #         except (IndexError, ValueError):
    #             continue # Ignora linhas mal formatadas ou sem valor
    # st.metric("Total ICMS (Registro D100 - Exemplo)", f"{total_icms_d100:.2f}")

    # TODO: Implementar totalizações por CST, CFOP, base de cálculo, etc.
    #       - Identificar os registros relevantes (ex: C100, C170, D100, etc.)
    #       - Mapear os campos corretos para cada totalização
    #       - Usar Pandas para agrupar e somar pode ser eficiente

    pass # Remover quando implementar a lógica 