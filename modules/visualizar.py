import streamlit as st

def display_file_content(corpo_sped, assinatura):
    """Exibe as primeiras 100 linhas do corpo do SPED."""
    st.subheader("Conteúdo do Arquivo (sem assinatura)")
    if corpo_sped:
        st.text("\n".join(corpo_sped[:100]))
        if len(corpo_sped) > 100:
            st.caption(f"... (mostrando 100 de {len(corpo_sped)} linhas do corpo)")
    else:
        st.info("Corpo do arquivo vazio ou não carregado.")

    # A informação sobre a assinatura pode ser mostrada na interface principal
    # if assinatura:
    #     st.info("Assinatura detectada e preservada.") 