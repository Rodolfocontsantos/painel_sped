import streamlit as st
import pandas as pd
from io import BytesIO
from utils import load_sped_layout # Importar para pegar nomes das colunas

def convert_to_spreadsheet(corpo_sped, assinatura):
    """Converte o corpo do SPED e oferece download como Excel (abas por registro) ou CSV (formato original)."""
    st.subheader("📄 Converter para Excel/CSV")

    if not corpo_sped:
        st.info("Carregue um arquivo SPED para converter.")
        return

    sped_layout = load_sped_layout()
    if not sped_layout:
        st.error("Layout SPED não carregado. Não é possível gerar o arquivo Excel com nomes de colunas.")
        # Ainda podemos gerar o CSV
    else:
        st.success("Layout SPED carregado. As colunas no Excel terão os nomes do layout.")

    # --- Preparação dos Dados para Excel (Opção B) --- #
    dataframes_por_registro = {}
    registros_encontrados = set()
    print("[DEBUG][Converter] Iniciando preparação para Excel...")

    if sped_layout: # Só tenta criar DFs estruturados se o layout foi carregado
        for idx, linha in enumerate(corpo_sped):
            if not linha.startswith('|'):
                continue
            partes = linha.split('|')
            if len(partes) < 2:
                continue
            registro = partes[1]

            # Log a cada 1000 linhas
            if idx % 1000 == 0:
                print(f"[DEBUG][Converter] Processando linha {idx+1} para Excel (Reg: {registro})")

            if registro in sped_layout:
                registros_encontrados.add(registro)
                if registro not in dataframes_por_registro:
                    # Cria lista para guardar as linhas (como dicionários)
                    dataframes_por_registro[registro] = []

                # Monta um dicionário para a linha atual
                linha_dict = {}
                campos_layout = sped_layout[registro]
                for nome_campo, indice_layout in campos_layout.items():
                    if indice_layout < len(partes):
                        linha_dict[nome_campo] = partes[indice_layout]
                    else:
                        linha_dict[nome_campo] = None # Ou string vazia ''

                dataframes_por_registro[registro].append(linha_dict)
            # else: # Registro não encontrado no layout, será ignorado no Excel
            #     pass

        print(f"[DEBUG][Converter] Dados agrupados por registro: {list(dataframes_por_registro.keys())}")

    # --- Botão de Download Excel --- #
    if dataframes_por_registro: # Se conseguimos processar com o layout
        try:
            output_excel = BytesIO()
            with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
                for registro, lista_linhas in dataframes_por_registro.items():
                    if lista_linhas:
                        print(f"[DEBUG][Converter] Criando DataFrame para registro {registro} com {len(lista_linhas)} linhas.")
                        # Define a ordem das colunas baseada no layout
                        col_order = list(sped_layout[registro].keys())
                        df_reg = pd.DataFrame(lista_linhas, columns=col_order)
                        # Nome da aba não pode ter caracteres inválidos e tem limite de tamanho
                        sheet_name = registro.replace(':', '_').replace('/', '_')[:31]
                        print(f"[DEBUG][Converter] Escrevendo aba: {sheet_name}")
                        df_reg.to_excel(writer, index=False, sheet_name=sheet_name)
                    else:
                        print(f"[DEBUG][Converter] Registro {registro} sem linhas para adicionar ao Excel.")

            excel_data = output_excel.getvalue()
            st.download_button(
                label="📥 Baixar como Excel (.xlsx) - Abas por Registro",
                data=excel_data,
                file_name="sped_convertido.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel"
            )
            print("[DEBUG][Converter] Botão de download Excel gerado.")
        except Exception as e:
            st.error(f"Erro ao gerar o arquivo Excel: {e}")
            print(f"[DEBUG][Converter] Erro Excel: {e}")
    elif sped_layout:
        st.info("Nenhum registro encontrado no arquivo SPED que corresponda ao layout carregado para gerar o Excel.")
    else:
         st.info("Layout não carregado, não é possível gerar o Excel estruturado.")


    # --- Botão de Download CSV (Separado por Ponto e Vírgula) --- #
    st.markdown("---")
    st.write("**Exportar como CSV (separado por ponto e vírgula):**")
    try:
        # Substitui '|' por ';' em cada linha e junta
        # Remove o primeiro e último caractere de cada linha se forem '|'
        linhas_modificadas = []
        for linha in corpo_sped:
            linha_limpa = linha
            if linha.startswith('|'):
                linha_limpa = linha_limpa[1:]
            if linha.endswith('|'):
                linha_limpa = linha_limpa[:-1]
            linhas_modificadas.append(linha_limpa.replace("|", ";"))

        csv_content_modificado = "\n".join(linhas_modificadas)

        # Codifica para latin-1 (ou utf-8 se preferir mais compatibilidade)
        # Usar latin-1 mantém a consistência com SPED, mas utf-8 é mais universal
        csv_data_modificado = csv_content_modificado.encode('latin-1', errors='replace')

        st.download_button(
            label="📥 Baixar como CSV (.csv) - Separador Ponto e Vírgula",
            data=csv_data_modificado,
            file_name="sped_convertido.csv", # Nome do arquivo .csv
            mime="text/csv",                # Mime type para CSV
            key="download_csv_modificado"
        )
        print("[DEBUG][Converter] Botão de download CSV modificado (;) gerado.")
    except Exception as e:
        st.error(f"Erro ao preparar o arquivo CSV modificado para download: {e}")
        print(f"[DEBUG][Converter] Erro CSV modificado: {e}")

    # Remover o placeholder original
    # st.warning("Funcionalidade de conversão ainda não implementada completamente.")

    pass # Remover quando implementar a lógica 