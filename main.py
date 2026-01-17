import streamlit as st
import pandas as pd

# Importar funções dos módulos
from utils import ler_e_separar_sped, baixar_arquivo
from modules.visualizar import display_file_content
from modules.alterar import handle_field_modification
from modules.resumo import generate_summary
from modules.converter import convert_to_spreadsheet

st.set_page_config(page_title="Painel SPED", layout="wide")
st.title("🧾 Painel de Manipulação de Arquivo SPED")

# --- Upload e Leitura do Arquivo ---
uploaded_file = st.file_uploader("📂 Envie seu arquivo SPED (.txt)", type=["txt"])

if uploaded_file is not None:
    # Usar st.session_state para manter os dados entre interações
    # Recarregar apenas se o nome do arquivo mudar
    if 'uploaded_filename' not in st.session_state or st.session_state.uploaded_filename != uploaded_file.name:
        st.session_state.corpo_sped, st.session_state.assinatura = ler_e_separar_sped(uploaded_file)
        st.session_state.uploaded_filename = uploaded_file.name
        # Mostrar mensagem sobre assinatura após a leitura inicial
        if st.session_state.assinatura is not None:
            if st.session_state.assinatura:
                 st.sidebar.success(f"Assinatura detectada e preservada.")
            else:
                 st.sidebar.warning("Assinatura não detectada ou formato não reconhecido.")

    # --- Menu Lateral e Chamada das Ações ---
    if st.session_state.get('corpo_sped') is not None: # Verifica se corpo foi carregado
        st.sidebar.title("Menu de Ações")
        acoes = [
            "Visualizar Arquivo",
            "Alterar Campos",
            "Gerar Resumo",
            "Converter para Excel/CSV"
        ]
        acao_selecionada = st.sidebar.radio(
            "Escolha o que deseja fazer:",
            acoes,
            key="acao_radio",
            # index=None # Descomentar se quiser que nada seja selecionado por padrão
        )

        # Container principal para exibir o conteúdo da ação
        main_container = st.container()

        with main_container:
            if acao_selecionada == "Visualizar Arquivo":
                display_file_content(st.session_state.corpo_sped, st.session_state.assinatura)

            elif acao_selecionada == "Alterar Campos":
                # A função de alteração retorna o corpo modificado
                novo_corpo = handle_field_modification(st.session_state.corpo_sped, st.session_state.assinatura)
                # Atualiza o estado da sessão se houve modificação REAL
                if novo_corpo is not st.session_state.corpo_sped: # Usar 'is not' para checar se é o mesmo objeto (lista)
                    st.session_state.corpo_sped = novo_corpo
                    st.success("Estado do arquivo atualizado na sessão.") # Feedback que a sessão foi atualizada
                    # st.rerun() # Opcional: Força rerun para UI refletir imediatamente, pode ter efeitos colaterais

            elif acao_selecionada == "Gerar Resumo":
                generate_summary(st.session_state.corpo_sped, st.session_state.assinatura)

            elif acao_selecionada == "Converter para Excel/CSV":
                convert_to_spreadsheet(st.session_state.corpo_sped, st.session_state.assinatura)

        # --- Download do Arquivo Atual (sempre disponível na sidebar) ---
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Arquivo Atual na Sessão:**")
        # Passa o nome original para o botão de download
        nome_arquivo_download = f"sped_atual_{st.session_state.uploaded_filename}" if st.session_state.get('uploaded_filename') else "sped_atual.txt"
        baixar_arquivo(st.session_state.corpo_sped, st.session_state.assinatura, nome_arquivo=nome_arquivo_download)

    else:
        # Se a leitura falhou (corpo_sped é None)
        st.warning("Não foi possível processar o arquivo. Verifique o formato ou tente novamente.")
        # Limpar estado para permitir novo upload
        for key in list(st.session_state.keys()):
            del st.session_state[key]

else:
    # Limpa o estado se nenhum arquivo estiver carregado (ou foi removido)
    if 'uploaded_filename' in st.session_state:
        st.info("Arquivo removido ou não carregado. Faça upload de um novo arquivo SPED .txt.")
        # Limpar estado completamente ao remover o arquivo
        for key in list(st.session_state.keys()):
            del st.session_state[key]
    else:
         st.info("Envie um arquivo SPED .txt para iniciar.") 

         