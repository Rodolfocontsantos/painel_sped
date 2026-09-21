import streamlit as st

from qt_backend import build_full_content
from services.sped_cleanup import (
    analyze_0200_duplicates,
    count_records,
    remove_0200_duplicates,
    remove_c101_records,
)


def _request_checkbox_reset(key):
    st.session_state[f"reset_{key}"] = True


def _apply_checkbox_reset(key):
    reset_key = f"reset_{key}"
    if st.session_state.pop(reset_key, False):
        st.session_state[key] = False


def _set_completed_action(action, removed_count):
    st.session_state.cleanup_pending = {
        "action": action,
        "removed_count": removed_count,
    }


def _clear_completed_action():
    st.session_state.pop("cleanup_pending", None)


@st.dialog("Confirmar remoção de duplicados", dismissible=False, icon=":material/warning:")
def _confirm_duplicate_removal():
    analysis = analyze_0200_duplicates(st.session_state.corpo_sped)
    if not analysis.duplicate_count:
        st.info("Não há registros 0200 duplicados para remover.")
        if st.button("Fechar", key="close_duplicate_dialog"):
            _request_checkbox_reset("remove_0200_checkbox")
            st.rerun()
        return

    if not analysis.removable_count:
        st.warning(
            "As ocorrências duplicadas possuem filhos em mais de um registro 0200. "
            "A remoção automática foi bloqueada para preservar a hierarquia do SPED."
        )
        if st.button("Fechar", key="close_protected_duplicate_dialog"):
            _request_checkbox_reset("remove_0200_checkbox")
            st.rerun()
        return

    st.warning(
        f"Serão removidos {analysis.removable_count} registros duplicados do 0200."
    )
    st.caption(
        "Será mantida a ocorrência que possui filhos; quando nenhuma possui filhos, "
        "será mantida a mais completa. Nenhuma linha será reposicionada."
    )
    if analysis.protected_group_count:
        st.info(
            f"{analysis.protected_group_count} grupos com filhos em mais de uma "
            "ocorrência não serão alterados automaticamente."
        )

    with st.container(horizontal=True):
        if st.button("Cancelar", key="cancel_duplicate_cleanup"):
            _request_checkbox_reset("remove_0200_checkbox")
            st.rerun()
        if st.button(
            "Confirmar remoção",
            type="primary",
            icon=":material/delete_sweep:",
            key="confirm_duplicate_cleanup",
        ):
            result = remove_0200_duplicates(
                st.session_state.corpo_sped,
                st.session_state.assinatura,
            )
            st.session_state.corpo_sped = result.corpo_sped
            st.session_state.assinatura = result.assinatura
            _request_checkbox_reset("remove_0200_checkbox")
            _set_completed_action("duplicados", result.removed_count)
            st.rerun()


@st.dialog("Confirmar remoção do DIFAL", dismissible=False, icon=":material/warning:")
def _confirm_c101_removal():
    c101_count = count_records(st.session_state.corpo_sped, "C101")
    if not c101_count:
        st.info("Não há registros C101 para remover.")
        if st.button("Fechar", key="close_c101_dialog"):
            _request_checkbox_reset("remove_c101_checkbox")
            st.rerun()
        return

    st.warning(
        f"Serão removidos {c101_count} registros C101. "
        "Os registros C100 correspondentes serão preservados."
    )

    with st.container(horizontal=True):
        if st.button("Cancelar", key="cancel_c101_cleanup"):
            _request_checkbox_reset("remove_c101_checkbox")
            st.rerun()
        if st.button(
            "Confirmar remoção",
            type="primary",
            icon=":material/delete_sweep:",
            key="confirm_c101_cleanup",
        ):
            result = remove_c101_records(
                st.session_state.corpo_sped,
                st.session_state.assinatura,
            )
            st.session_state.corpo_sped = result.corpo_sped
            st.session_state.assinatura = result.assinatura
            _request_checkbox_reset("remove_c101_checkbox")
            _set_completed_action("difal", result.removed_count)
            st.rerun()


@st.dialog("Alterações concluídas", dismissible=False, icon=":material/check_circle:")
def _show_completed_action_dialog(pending):
    removed_count = pending["removed_count"]
    action = pending["action"]
    description = "duplicados do registro 0200" if action == "duplicados" else "registros C101"
    st.success(f"Foram removidos {removed_count} {description} e os totalizadores foram ajustados.")
    st.write("Você pode salvar o novo arquivo agora ou continuar editando na sessão atual.")

    content = build_full_content(
        st.session_state.corpo_sped,
        st.session_state.assinatura,
    )
    original_name = st.session_state.get("uploaded_filename", "sped.txt")
    prefix = "sped_sem_duplicados_" if action == "duplicados" else "sped_sem_difal_"

    with st.container(horizontal=True):
        st.download_button(
            "Salvar novo arquivo",
            data=content.encode("latin-1"),
            file_name=f"{prefix}{original_name}",
            mime="text/plain",
            type="primary",
            icon=":material/download:",
            key=f"download_cleanup_{action}",
            on_click=_clear_completed_action,
        )
        if st.button(
            "Continuar editando",
            icon=":material/edit:",
            key=f"continue_cleanup_{action}",
        ):
            _clear_completed_action()
            st.rerun()


def render_duplicate_removal(corpo_sped):
    st.subheader("Remover duplicados do registro 0200")
    analysis = analyze_0200_duplicates(corpo_sped)

    if not analysis.duplicate_count:
        st.success("O arquivo não contém registros duplicados no 0200.")
    else:
        st.warning(
            f"O arquivo contém {analysis.duplicate_count} registros duplicados no registro 0200."
        )
        if analysis.removable_count:
            st.caption(
                f"{analysis.removable_count} duplicados podem ser removidos sem "
                "reposicionar registros filhos."
            )
        if analysis.conflicting_group_count:
            st.caption(
                f"{analysis.conflicting_group_count} grupos possuem campos conflitantes."
            )
        if analysis.protected_group_count:
            st.warning(
                f"{analysis.protected_group_count} grupos possuem filhos em mais de uma "
                "ocorrência e não serão removidos automaticamente."
            )

    checkbox_key = "remove_0200_checkbox"
    _apply_checkbox_reset(checkbox_key)
    confirmed = st.checkbox(
        "Remover duplicados sem reposicionar registros filhos",
        key=checkbox_key,
        disabled=not analysis.removable_count,
    )
    if confirmed:
        _confirm_duplicate_removal()


def render_c101_removal(corpo_sped):
    st.subheader("Remover DIFAL")
    c101_count = count_records(corpo_sped, "C101")

    if c101_count:
        st.warning(f"O arquivo contém {c101_count} registros C101.")
    else:
        st.success("O arquivo não contém registros C101.")

    checkbox_key = "remove_c101_checkbox"
    _apply_checkbox_reset(checkbox_key)
    confirmed = st.checkbox(
        "Remover somente os registros C101",
        key=checkbox_key,
        disabled=not c101_count,
    )
    if confirmed:
        _confirm_c101_removal()


def render_completed_action_dialog():
    pending = st.session_state.get("cleanup_pending")
    if pending:
        _show_completed_action_dialog(pending)
