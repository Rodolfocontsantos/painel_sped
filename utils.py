import streamlit as st
import os # Pode ser útil para futuras funções de utilidade

def ler_e_separar_sped(uploaded_file):
    """Lê o arquivo SPED, separa o corpo da assinatura e retorna ambos."""
    try:
        conteudo = uploaded_file.read().decode("latin-1")
        linhas = conteudo.splitlines()
    except Exception as e:
        st.error(f"Erro ao ler o arquivo: {e}")
        return None, None

    assinatura_idx = None
    for i, linha in enumerate(linhas):
        # Procura por um padrão mais genérico de assinatura (início de bloco 9)
        if linha.startswith("|9") and len(linha.split('|')) > 2 and linha.split('|')[1].startswith('9'):
             # Verifica se é o último bloco antes do |9999|
            is_last_block = True
            for next_line in linhas[i+1:]:
                if next_line.startswith('|') and not next_line.startswith('|9'):
                    is_last_block = False
                    break
            if is_last_block:
                 # Consideramos o início do bloco 9 como separador
                 assinatura_idx = i
                 break # Assume que o primeiro bloco 9 encontrado no final é a assinatura

    if assinatura_idx is not None:
        corpo_sped = linhas[:assinatura_idx]
        assinatura = linhas[assinatura_idx:]
        # A mensagem pode ser movida para a interface principal se preferir
        # st.info(f"Assinatura (a partir da linha {assinatura_idx + 1}) detectada e preservada.")
    else:
        corpo_sped = linhas
        assinatura = []
        # A mensagem pode ser movida para a interface principal se preferir
        # st.warning("Assinatura não detectada ou formato não reconhecido. O arquivo será tratado como um todo.")

    return corpo_sped, assinatura

def baixar_arquivo(corpo_sped, assinatura, nome_arquivo="sped_processado.txt"):
    """Gera o botão de download para o arquivo SPED (corpo + assinatura)."""
    if corpo_sped is None:
        st.warning("Não há dados para baixar.")
        return

    novo_conteudo = "\n".join(corpo_sped + assinatura)
    st.download_button(
        label="💾 Baixar Arquivo Processado",
        data=novo_conteudo.encode("latin-1"),
        file_name=nome_arquivo,
        mime="text/plain"
    )

# Poderíamos adicionar mais funções utilitárias aqui no futuro
# Ex: função para validar formato de linha SPED, etc.

@st.cache_data # Cache para evitar ler o arquivo descritivo toda hora
def load_sped_layout(file_path="sped_descricao/sped_descritivo.txt"):
    """ Lê o arquivo descritivo do layout SPED e retorna um dicionário
        mapeando REGISTRO -> {NOME_CAMPO: indice_base_1}.
    """
    layout = {}
    print(f"[DEBUG] Tentando carregar layout de: {file_path}") # Log inicial
    try:
        with open(file_path, 'r', encoding='utf-8') as f: # Usar utf-8 por segurança
            for line_num, line in enumerate(f):
                line = line.strip()
                if not line or not line.startswith('|'):
                    continue

                try:
                    parts = line.split('|')
                    # Esperado: ['', REGISTRO, CAMPO1, CAMPO2, ..., '', '']
                    if len(parts) < 4:
                        print(f"[DEBUG] Layout: Linha {line_num+1} ignorada (formato inválido - poucas partes): {line[:50]}...")
                        continue

                    registro = parts[1]
                    # Os campos estão de parts[2] até parts[-3] ? Verificar o último `|`
                    # Se a linha termina com ||, parts[-1] e parts[-2] serão vazios.
                    campos = parts[2:-2] # Correto se termina com ||

                    if not registro: # Ignora se o registro for vazio
                        print(f"[DEBUG] Layout: Linha {line_num+1} ignorada (registro vazio): {line[:50]}...")
                        continue

                    layout[registro] = {}
                    for i, nome_campo in enumerate(campos):
                        if nome_campo: # Ignora campos vazios no descritivo
                            layout[registro][nome_campo] = i + 2 # Índice baseado em 1 (posição após split)
                    # print(f"[DEBUG] Layout: Registro {registro} carregado com {len(campos)} campos.") # Log por registro (pode ser muito)
                except Exception as inner_e:
                     print(f"[DEBUG] Layout: Erro processando linha {line_num+1}: {line[:50]}... Erro: {inner_e}")
                     continue # Pula para próxima linha

        if not layout:
            st.error(f"Nenhum layout válido carregado de {file_path}. Verifique o arquivo.")
            print(f"[DEBUG] Nenhum layout carregado de {file_path}")
            return None
        print(f"[DEBUG] Layout SPED carregado com {len(layout)} registros.")
        return layout

    except FileNotFoundError:
        st.error(f"Arquivo descritivo do layout SPED não encontrado em: {file_path}")
        return None
    except Exception as e:
        st.error(f"Erro ao ler o arquivo descritivo do layout SPED ({file_path}): {e}")
        return None 