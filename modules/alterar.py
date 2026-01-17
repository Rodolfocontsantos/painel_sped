import streamlit as st
import pandas as pd # Importar pandas se for usado para preview ou validação futura
from utils import baixar_arquivo, load_sped_layout # Importar load_sped_layout

def handle_field_modification(corpo_sped, assinatura):
    """Interface e lógica para alterar campos específicos no SPED usando layout dinâmico."""
    st.subheader("✏️ Alterar Campos Específicos")

    # Carrega o layout do arquivo descritivo
    print("[DEBUG] Entrando em handle_field_modification") # Log
    sped_layout = load_sped_layout() # Usa o caminho padrão "sped_descricao/sped_descritivo.txt"
    if not sped_layout:
        st.error("Não foi possível carregar o layout do SPED. Verifique o arquivo descritivo.")
        print("[DEBUG] Layout não carregado, saindo de handle_field_modification") # Log
        return corpo_sped # Não pode continuar sem layout
    print("[DEBUG] Layout SPED carregado em handle_field_modification") # Log

    # Tenta extrair todos os tipos de registro do corpo
    tipos_registro = []
    print("[DEBUG] Iniciando extração de tipos de registro...") # Log
    try:
        tipos_registro = sorted(list(set(l.split('|')[1] for l in corpo_sped if l.startswith('|') and len(l.split('|')) > 1 and l.split('|')[1] in sped_layout)))
        # Filtra para mostrar apenas registros que existem no layout carregado
        print(f"[DEBUG] Tipos de registro encontrados no SPED e no layout: {tipos_registro}") # Log
    except IndexError as ie:
        st.warning("Erro de índice ao processar registros. Verifique o formato do arquivo SPED.")
        print(f"[DEBUG] Erro de índice ao extrair tipos de registro: {ie}") # Log
    except Exception as e:
        st.error(f"Erro inesperado ao ler registros: {e}")
        print(f"[DEBUG] Erro geral ao extrair tipos de registro: {e}") # Log

    if not tipos_registro:
        st.warning("Nenhum tipo de registro válido (presente no layout) encontrado no corpo do arquivo.")
        return corpo_sped

    # --- Seleção de Registro ---
    registro_escolhido = st.selectbox(
        "1. Escolha o Tipo de Registro:",
        tipos_registro,
        index=None,
        placeholder="Selecione o registro...",
        help="Apenas registros presentes no arquivo e no layout são mostrados.",
        key="select_registro"
    )

    if not registro_escolhido:
        st.info("Selecione um tipo de registro para definir filtros e campos.")
        return corpo_sped

    # --- Filtros Dinâmicos (Baseado nos campos do layout para o registro escolhido) ---
    st.markdown("**2. Filtros (Opcional):**")
    campos_registro_atual = sped_layout.get(registro_escolhido, {})
    filtros_ativos = {}

    # Define alguns campos comuns para filtro rápido (pode ser expandido)
    campos_filtro_sugeridos = ["CFOP", "CST_ICMS", "COD_ITEM", "NUM_DOC", "CHV_NFE", "CHV_CTE"]
    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]
    col_idx = 0

    for nome_campo in campos_registro_atual.keys():
        if nome_campo in campos_filtro_sugeridos:
            with cols[col_idx % 3]:
                 valor_filtro = st.text_input(f"Filtrar por {nome_campo}", key=f"filtro_{registro_escolhido}_{nome_campo}")
                 if valor_filtro:
                     # Armazena o índice base 1 do layout
                     indice_campo = campos_registro_atual[nome_campo]
                     filtros_ativos[indice_campo] = valor_filtro
            col_idx += 1

    # Adicionar um filtro genérico por texto (busca em qualquer campo da linha)
    filtro_geral = st.text_input("Filtrar por texto em qualquer parte da linha", key=f"filtro_geral_{registro_escolhido}")

    # --- Filtragem das Linhas --- #
    linhas_filtradas_indices = [] # Guarda tupla (índice original, linha completa)
    linhas_para_mostrar = []      # Guarda tupla (índice original, texto preview)
    print(f"[DEBUG] Iniciando filtragem para registro {registro_escolhido}...") # Log

    for idx, l in enumerate(corpo_sped):
        if l.startswith(f"|{registro_escolhido}|"):
            # Log a cada X linhas para não poluir muito
            if idx % 1000 == 0:
                print(f"[DEBUG] Filtrando linha {idx+1}...")
            partes = l.split("|")
            try:
                match_all_filters = True
                # Verifica filtros específicos por campo
                for indice_campo_layout, valor_filtro in filtros_ativos.items():
                    # Valida se o índice do layout existe na linha atual
                    if not (indice_campo_layout < len(partes) and valor_filtro in partes[indice_campo_layout]):
                        match_all_filters = False
                        break
                # Verifica filtro geral (se todos os filtros específicos passaram)
                if match_all_filters and filtro_geral:
                    if filtro_geral not in l:
                        match_all_filters = False

                if match_all_filters:
                    linhas_filtradas_indices.append((idx, l))
                    # Cria preview mostrando a linha completa, sem número
                    # Usamos 'l' diretamente pois já é a linha original completa
                    preview_txt = l
                    linhas_para_mostrar.append((idx, preview_txt))

            except IndexError:
                 st.warning(f"Linha {idx+1} do registro {registro_escolhido} parece mal formatada. Pulando filtros.")
                 print(f"[DEBUG] Warning: Linha {idx+1} mal formatada (IndexError) no filtro: {l[:50]}...") # Log
                 continue
            except Exception as e:
                 st.error(f"Erro ao processar linha {idx+1}: {e}")
                 print(f"[DEBUG] Erro processando linha {idx+1} no filtro: {e} - Linha: {l[:50]}...") # Log
                 continue

    print(f"[DEBUG] Filtragem concluída. {len(linhas_filtradas_indices)} linhas encontradas.") # Log
    st.markdown(f"#### {len(linhas_filtradas_indices)} Registros Encontrados para '{registro_escolhido}' (após filtros)")
    aplicar_em_todos = st.checkbox("✅ Aplicar a alteração em todos os registros filtrados (ignorar seleção manual)")


    if not linhas_filtradas_indices:
        st.info("Nenhuma linha corresponde aos filtros aplicados.")
        return corpo_sped

    # --- Seleção de Linhas --- #
    st.markdown("**3. Selecione os Registros para Alterar:**")
    selecionados_indices_set = set(st.session_state.get(f'selecionados_{registro_escolhido}', [])) # Usa um set para gestão

    with st.expander("Mostrar/Ocultar Registros Filtrados", expanded=True):
        select_all_key = f'select_all_val_{registro_escolhido}'
        select_all_state = st.session_state.get(select_all_key, False)
        select_all = st.checkbox("Selecionar/Deselecionar Todos Visíveis Nesta Página", value=select_all_state, key=f"select_all_cb_{registro_escolhido}")
        st.session_state[select_all_key] = select_all # Atualiza o estado

        st.write("--- Registros Filtrados ---")
        # Paginação simples
        items_per_page = 50
        total_items = len(linhas_para_mostrar)
        total_pages = (total_items + items_per_page - 1) // items_per_page
        page_number = st.number_input('Página', min_value=1, max_value=max(1, total_pages), value=1, step=1, key=f'page_{registro_escolhido}')

        start_idx = (page_number - 1) * items_per_page
        end_idx = start_idx + items_per_page
        linhas_pagina_atual = linhas_para_mostrar[start_idx:end_idx]
        indices_pagina_atual = {idx for idx, _ in linhas_pagina_atual} # Set dos índices na página atual

        # Lógica para aplicar/desaplicar Select All APENAS na página atual
        aplicar_select_all_nesta_pagina = st.session_state.get(f'select_all_pressed_{registro_escolhido}', False)
        if select_all != st.session_state.get(f'last_select_all_state_{registro_escolhido}', None):
             aplicar_select_all_nesta_pagina = True
             st.session_state[f'last_select_all_state_{registro_escolhido}'] = select_all

        for original_idx, preview_txt in linhas_pagina_atual:
            chave_checkbox = f"chk_{original_idx}"
            is_selected = original_idx in selecionados_indices_set

            # Inicializa só no primeiro render daquele item
            if chave_checkbox not in st.session_state:
                st.session_state[chave_checkbox] = is_selected

            # >>> ponto crucial: FORCE o estado quando "Selecionar todos" mudar
            if aplicar_select_all_nesta_pagina:
                st.session_state[chave_checkbox] = select_all

            # Agora renderiza SEM 'value=', pois o estado já está em session_state
            selecionado = st.checkbox(preview_txt, key=chave_checkbox)

            # Sincroniza o set global conforme o estado do widget
            if selecionado:
                selecionados_indices_set.add(original_idx)
            else:
                selecionados_indices_set.discard(original_idx)
                
        # Reseta o flag de aplicação do select all da página
        st.session_state[f'select_all_pressed_{registro_escolhido}'] = False

        # Guarda o set atualizado na session state (convertido para lista para serialização)
        st.session_state[f'selecionados_{registro_escolhido}'] = list(selecionados_indices_set)

        st.caption(f"Mostrando {len(linhas_pagina_atual)} de {total_items} registros filtrados (Página {page_number}/{total_pages}). Total selecionado: {len(selecionados_indices_set)}")

    st.markdown("---") # Separador visual

    # --- Aplicação da Alteração --- #
    st.markdown("**4. Defina a Alteração:**")
    campos_alteraveis = list(campos_registro_atual.keys())

    if not campos_alteraveis:
        st.info(f"Não há campos definidos no layout para alteração no registro {registro_escolhido}.")
        return corpo_sped

    col_campo, col_valor = st.columns(2)
    with col_campo:
        campo_nome = st.selectbox(
            "Qual campo deseja alterar?",
            campos_alteraveis,
            index=None,
            placeholder="Selecione o campo...",
            key=f"campo_alt_{registro_escolhido}"
        )
    with col_valor:
        help_text = f"Posição (base 1): {campos_registro_atual.get(campo_nome, 'N/A')} no registro {registro_escolhido}"
        # Correção da f-string aqui:
        novo_valor = st.text_input(
            f"Novo valor para '{campo_nome or ""}'?", # f-string corrigida
            help=help_text,
            key=f"valor_alt_{registro_escolhido}"
        )

    # Usa o set atualizado para verificar se algo está selecionado
    aplicar_desabilitado = not selecionados_indices_set or not campo_nome
    if st.button("Aplicar Alteração nos Registros Selecionados", disabled=aplicar_desabilitado, key=f"btn_aplicar_{registro_escolhido}"):

        if not campo_nome: # Verificação extra
            st.warning("Selecione um campo para alterar.")
            return corpo_sped

        indice_campo_alterar = campos_registro_atual[campo_nome] # Índice base 1
        linhas_modificadas_count = 0
        novo_corpo_sped = list(corpo_sped) # Cria cópia para modificar
        linhas_alteradas_preview_list = []
        erros_alteracao = []

        # Usa os índices do set que está no session state
        if aplicar_em_todos:
            indices_para_alterar = [idx for idx, _ in linhas_filtradas_indices]
        else:
            indices_para_alterar = list(st.session_state.get(f'selecionados_{registro_escolhido}', []))
            if not indices_para_alterar:
                st.warning("Nenhum registro está selecionado para aplicar a alteração.")
                return corpo_sped


        for idx_original in indices_para_alterar:
            if idx_original >= len(novo_corpo_sped):
                erros_alteracao.append(f"Índice {idx_original+1} inválido (maior que o tamanho do arquivo?). Pulando.")
                continue

            linha_original = novo_corpo_sped[idx_original]
            # Verifica se a linha ainda é do registro esperado (segurança)
            if not linha_original.startswith(f"|{registro_escolhido}|"):
                 erros_alteracao.append(f"Linha {idx_original+1} não parece ser mais do registro {registro_escolhido}. Alteração pulada.")
                 continue

            partes = linha_original.split("|")

            if indice_campo_alterar < len(partes):
                # TODO: Adicionar validação do novo_valor baseado no tipo de campo esperado
                if partes[indice_campo_alterar] != novo_valor:
                    partes[indice_campo_alterar] = novo_valor
                    linha_modificada = "|".join(partes)
                    novo_corpo_sped[idx_original] = linha_modificada
                    linhas_modificadas_count += 1
                    linhas_alteradas_preview_list.append(f"L{idx_original+1}: {linha_modificada}")
            else:
                erros_alteracao.append(f"Linha {idx_original+1} ('{linha_original[:50]}...') não possui o campo '{campo_nome}' na posição esperada ({indice_campo_alterar}) pelo layout. Alteração pulada.")

        if erros_alteracao:
            st.markdown("**Avisos durante a alteração:**")
            for erro in erros_alteracao:
                st.warning(erro)

        if linhas_modificadas_count > 0:
            st.success(f"{linhas_modificadas_count} registros foram atualizados com sucesso na memória!")
            with st.expander("Ver Pré-visualização das Linhas Alteradas"):
                 st.text("\n".join(linhas_alteradas_preview_list))

            st.markdown("**Download do Arquivo com Alterações:**")
            baixar_arquivo(novo_corpo_sped, assinatura, nome_arquivo=f"sped_{registro_escolhido}_alterado.txt")
            # Limpa seleção após aplicar com sucesso
            st.session_state[f'selecionados_{registro_escolhido}'] = []
            st.session_state[select_all_key] = False # Desmarca o select all
            # st.rerun() # Opcional: Forçar rerun para limpar checkboxes visualmente
            return novo_corpo_sped
        else:
            st.info("Nenhum registro precisou ser modificado (o novo valor já era o existente ou houve avisos).")
            return corpo_sped

    return corpo_sped 