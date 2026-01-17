import sys
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QMessageBox,
    QStyle,
)

import qt_backend as backend
from ui_nova import UiMainWindowNova, FilteredLinesModel


class PandasModel(QAbstractTableModel):
    def __init__(self, df=None):
        super().__init__()
        self._df = df

    def set_dataframe(self, df):
        self.beginResetModel()
        self._df = df
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        if self._df is None:
            return 0
        return len(self._df.index)

    def columnCount(self, parent=QModelIndex()):
        if self._df is None:
            return 0
        return len(self._df.columns)

    def data(self, index, role=Qt.DisplayRole):
        if self._df is None or not index.isValid():
            return None
        if role == Qt.DisplayRole:
            value = self._df.iat[index.row(), index.column()]
            return str(value)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if self._df is None or role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return str(self._df.columns[section])
        return str(self._df.index[section])


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Painel SPED - Qt (Nova)")

        self.corpo_sped = None
        self.assinatura = None
        self.layout = None
        self.filtered_lines = []
        self.last_modified_body = None
        self.theme = "system"

        self.ui = UiMainWindowNova()
        self.ui.setup_ui(self)
        self._connect_signals()
        self._apply_theme()
        self._sync_watermark_style()
        app = QApplication.instance()
        if app is not None:
            app.styleHints().colorSchemeChanged.connect(self._on_system_theme_change)

    def _connect_signals(self):
        self.ui.btn_upload.clicked.connect(self._on_upload)
        self.ui.btn_save_current.clicked.connect(self._on_save_current)
        self.ui.menu.currentRowChanged.connect(self._on_menu_change)
        self.ui.menu.setCurrentRow(0)
        self.ui.btn_theme_toggle.clicked.connect(self._toggle_theme)

        self.ui.combo_registro.currentTextChanged.connect(self._on_registro_change)
        for _, edit in self.ui.filter_inputs.values():
            edit.textChanged.connect(self._on_filters_change)
        self.ui.edit_filtro_geral.textChanged.connect(self._on_filters_change)
        self.ui.btn_apply.clicked.connect(self._on_apply_change)
        self.ui.btn_save_altered.clicked.connect(self._on_save_altered)

        self.model_lines = FilteredLinesModel()
        self.ui.table_lines.setModel(self.model_lines)

        self.model_cfop = PandasModel()
        self.model_tipo = PandasModel()
        self.ui.view_cfop.setModel(self.model_cfop)
        self.ui.view_tipo.setModel(self.model_tipo)

        self.ui.btn_export_excel.clicked.connect(self._on_export_excel)
        self.ui.btn_export_csv.clicked.connect(self._on_export_csv)

    def _on_menu_change(self, index):
        self.ui.pages.setCurrentIndex(index)

    def _apply_theme(self):
        app = QApplication.instance()
        if app is None:
            return
        app.setStyleSheet("")
        effective = self._effective_theme()
        app.setStyleSheet(get_stylesheet(effective))
        if effective == "light":
            self.ui.btn_theme_toggle.setText("☾")
            self.ui.btn_theme_toggle.setToolTip("Ativar modo escuro")
            self.ui.btn_theme_toggle.setStyleSheet(
                "color: rgba(200, 150, 40, 170);"
                "border: 1px solid rgba(200, 150, 40, 170);"
                "background: transparent;"
                "padding: 0;"
            )
        else:
            self.ui.btn_theme_toggle.setText("☀")
            self.ui.btn_theme_toggle.setToolTip("Ativar modo claro")
            self.ui.btn_theme_toggle.setStyleSheet(
                "color: rgba(230, 150, 40, 170);"
                "border: 1px solid rgba(230, 150, 40, 170);"
                "background: transparent;"
                "padding: 0;"
            )
        self._sync_watermark_style()
        self.style().unpolish(self)
        self.style().polish(self)

    def _toggle_theme(self):
        effective = self._effective_theme()
        self.theme = "dark" if effective == "light" else "light"
        self._apply_theme()


    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.centralWidget():
            return
        label = self.ui.watermark_label
        margin = 12
        label.adjustSize()
        x = margin
        y = self.centralWidget().height() - label.height() - margin
        label.move(max(x, margin), max(y, margin))
        label.raise_()

    def _sync_watermark_style(self):
        if self._effective_theme() == "dark":
            self.ui.watermark_label.setStyleSheet(
                "color: rgba(212, 175, 55, 220);"
                "font-family: 'Segoe Script';"
                "font-size: 12px;"
                "font-weight: bold;"
            )
        else:
            self.ui.watermark_label.setStyleSheet(
                "color: #4169E1;"
                "font-family: 'Segoe Script';"
                "font-size: 12px;"
                "font-weight: bold;"
            )

    def _effective_theme(self):
        if self.theme in ("light", "dark"):
            return self.theme
        app = QApplication.instance()
        if app is None:
            return "light"
        return "dark" if app.styleHints().colorScheme() == Qt.ColorScheme.Dark else "light"

    def _on_system_theme_change(self, _):
        if self.theme == "system":
            self._apply_theme()

    def _on_upload(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open SPED file", "", "SPED (*.txt)")
        if not file_path:
            return
        try:
            self.corpo_sped, self.assinatura = backend.read_sped_file(file_path)
            self.layout = backend.load_sped_layout()
            self.ui.lbl_file.setText(file_path)
            self.ui.btn_save_current.setEnabled(True)
            self.last_modified_body = None
            self._refresh_all()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {e}")

    def _on_save_current(self):
        if not self.corpo_sped:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Save SPED file", "", "SPED (*.txt)")
        if not file_path:
            return
        content = backend.build_full_content(self.corpo_sped, self.assinatura)
        with open(file_path, "wb") as f:
            f.write(content.encode("latin-1", errors="replace"))

    def _on_save_altered(self):
        if not self.last_modified_body:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Save altered file", "", "SPED (*.txt)")
        if not file_path:
            return
        content = backend.build_full_content(self.last_modified_body, self.assinatura)
        with open(file_path, "wb") as f:
            f.write(content.encode("latin-1", errors="replace"))

    def _refresh_all(self):
        self._refresh_view()
        self._refresh_registros()
        self._refresh_summary()
        self._refresh_convert_status()

    def _refresh_view(self):
        if not self.corpo_sped:
            self.ui.view_text.setPlainText("No file loaded")
            return
        self.ui.view_text.setPlainText("\n".join(self.corpo_sped[:100]))

    def _refresh_registros(self):
        self.ui.combo_registro.blockSignals(True)
        self.ui.combo_registro.clear()
        if not self.corpo_sped or not self.layout:
            self.ui.combo_registro.blockSignals(False)
            return
        registros = sorted(
            {
                l.split("|")[1]
                for l in self.corpo_sped
                if l.startswith("|") and len(l.split("|")) > 1 and l.split("|")[1] in self.layout
            }
        )
        self.ui.combo_registro.addItems(registros)
        self.ui.combo_registro.blockSignals(False)
        if registros:
            self.ui.combo_registro.setCurrentIndex(0)
        self._on_registro_change(self.ui.combo_registro.currentText())

    def _on_registro_change(self, registro):
        if not registro or not self.layout:
            return
        campos = self.layout.get(registro, {})
        for field, (lbl, edit) in self.ui.filter_inputs.items():
            visible = field in campos
            lbl.setVisible(visible)
            edit.setVisible(visible)
            if not visible:
                edit.setText("")

        self.ui.combo_campo.blockSignals(True)
        self.ui.combo_campo.clear()
        self.ui.combo_campo.addItems(list(campos.keys()))
        self.ui.combo_campo.blockSignals(False)

        self.model_lines.clear_selection()
        self._apply_filters()

    def _on_filters_change(self):
        self._apply_filters()

    def _apply_filters(self):
        registro = self.ui.combo_registro.currentText()
        if not registro or not self.layout or not self.corpo_sped:
            self.filtered_lines = []
            self.model_lines.set_lines([])
            self.ui.lbl_page_info.setText("0 items")
            return
        filtros_ativos = {}
        campos = self.layout.get(registro, {})
        for field, (lbl, edit) in self.ui.filter_inputs.items():
            if field in campos and edit.text():
                filtros_ativos[campos[field]] = edit.text()
        filtro_geral = self.ui.edit_filtro_geral.text()
        self.filtered_lines = backend.filter_lines(
            self.corpo_sped, registro, filtros_ativos, filtro_geral
        )
        self.model_lines.set_lines(self.filtered_lines)
        self.ui.table_lines.resizeColumnToContents(0)
        width = max(self.ui.table_lines.columnWidth(0), 32)
        self.ui.table_lines.setColumnWidth(0, width)
        self._align_apply_checkbox()
        self.ui.lbl_page_info.setText(f"{len(self.filtered_lines)} items")

    def _align_apply_checkbox(self):
        if not hasattr(self.ui, "apply_all_spacer"):
            return
        col_width = self.ui.table_lines.columnWidth(0)
        indicator = self.ui.check_apply_all.style().pixelMetric(QStyle.PM_IndicatorWidth)
        offset = max(0, int((col_width - indicator) / 2) + 4)
        self.ui.apply_all_spacer.setFixedWidth(offset)

    def _on_apply_change(self):
        registro = self.ui.combo_registro.currentText()
        campo = self.ui.combo_campo.currentText()
        novo_valor = self.ui.edit_novo_valor.text()
        if not registro or not campo or not self.layout or not self.corpo_sped:
            self.ui.lbl_status.setText("Missing registro/campo/file.")
            return

        indice_campo = self.layout[registro][campo]
        if self.ui.check_apply_all.isChecked():
            indices_para_alterar = [idx for idx, _ in self.filtered_lines]
        else:
            indices_para_alterar = list(self.model_lines.selected_indices())
        if not indices_para_alterar:
            self.ui.lbl_status.setText("No lines selected.")
            return

        (
            novo_corpo,
            modificadas,
            erros,
            preview,
        ) = backend.apply_field_change(
            self.corpo_sped, registro, indice_campo, novo_valor, indices_para_alterar
        )
        self.corpo_sped = novo_corpo
        self.last_modified_body = novo_corpo if modificadas > 0 else self.last_modified_body
        self.ui.btn_save_altered.setEnabled(self.last_modified_body is not None)
        self.ui.lbl_status.setText(f"Modified lines: {modificadas}")
        self.ui.preview_text.setPlainText("\n".join(preview[-200:]))
        if erros:
            QMessageBox.warning(self, "Warnings", "\n".join(erros[:10]))
        self._refresh_view()
        self._apply_filters()

    def _refresh_summary(self):
        if not self.corpo_sped or not self.layout:
            self.ui.lbl_total_bc.setText("Total BC ICMS: -")
            self.ui.lbl_total_icms.setText("Total ICMS: -")
            self.ui.lbl_total_linhas.setText("Total linhas: -")
            self.model_cfop.set_dataframe(None)
            self.model_tipo.set_dataframe(None)
            return
        summary = backend.build_summary(self.corpo_sped, self.layout)
        if not summary:
            self.ui.lbl_total_bc.setText("Total BC ICMS: -")
            self.ui.lbl_total_icms.setText("Total ICMS: -")
            self.ui.lbl_total_linhas.setText("Total linhas: -")
            self.model_cfop.set_dataframe(None)
            self.model_tipo.set_dataframe(None)
            return
        self.ui.lbl_total_bc.setText(f"Total BC ICMS: {summary['total_bc_icms']:.2f}")
        self.ui.lbl_total_icms.setText(f"Total ICMS: {summary['total_icms']:.2f}")
        self.ui.lbl_total_linhas.setText(f"Total linhas: {summary['total_linhas']}")
        self.model_cfop.set_dataframe(summary["resumo_cfop"])
        self.model_tipo.set_dataframe(summary["resumo_tipo_op"])

    def _refresh_convert_status(self):
        if not self.corpo_sped:
            self.ui.lbl_convert_status.setText("No file loaded.")
        else:
            self.ui.lbl_convert_status.setText("")

    def _on_export_excel(self):
        if not self.corpo_sped or not self.layout:
            self.ui.lbl_convert_status.setText("Load a file first.")
            return
        excel_bytes = backend.build_excel_bytes(self.corpo_sped, self.layout)
        if not excel_bytes:
            self.ui.lbl_convert_status.setText("No matching records for Excel.")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Excel", "", "Excel (*.xlsx)")
        if not file_path:
            return
        with open(file_path, "wb") as f:
            f.write(excel_bytes)
        self.ui.lbl_convert_status.setText("Excel saved.")

    def _on_export_csv(self):
        if not self.corpo_sped:
            self.ui.lbl_convert_status.setText("Load a file first.")
            return
        csv_bytes = backend.build_csv_bytes(self.corpo_sped)
        file_path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV (*.csv)")
        if not file_path:
            return
        with open(file_path, "wb") as f:
            f.write(csv_bytes)
        self.ui.lbl_convert_status.setText("CSV saved.")


def get_stylesheet(theme):
    base = """
        * {{
            font-family: "Segoe UI";
            font-size: 13px;
        }}
        QPushButton {{
            background: #ff4b4b;
            color: #ffffff;
            border: none;
            padding: 8px 12px;
            border-radius: 6px;
            font-weight: 600;
        }}
        QPushButton:disabled {{
            background: #ffd2d2;
            color: #ffffff;
        }}
        QPushButton#SecondaryButton {{
            background: {secondary_bg};
            color: {text};
            border: 1px solid {border};
        }}
        QPushButton#ThemeToggle {{
            background: transparent;
            border: 1px solid {toggle_border};
            padding: 0;
            color: {toggle_text};
        }}
        QListWidget {{
            background: {panel};
            border: 1px solid {border};
            border-radius: 6px;
            color: {list_text};
        }}
        QListWidget::item {{
            padding: 8px;
            color: {list_text};
        }}
        QListWidget::item:selected {{
            background: {accent_bg};
            color: {list_text};
        }}
        QLineEdit, QComboBox, QTextEdit, QTableView {{
            background: {panel};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 6px;
            color: {text};
        }}
        QHeaderView::section {{
            background: {header_bg};
            border: none;
            padding: 6px;
            color: {muted};
        }}
        QGroupBox {{
            border: 1px solid {border};
            border-radius: 8px;
            margin-top: 10px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
            color: {muted};
            font-weight: 600;
        }}
        QCheckBox {{
            padding: 4px;
            color: {text};
        }}
    """

    if theme == "dark":
        return (
            """
            QMainWindow {
                background: #0e1117;
            }
            QWidget#Sidebar {
                background: #111827;
                border-right: 1px solid #1f2937;
            }
            QLabel {
                color: #e5e7eb;
                font-weight: 600;
            }
            """
            + base.format(
                panel="#111827",
                border="#2b3340",
                text="#e5e7eb",
                muted="#cbd5e1",
                header_bg="#1f2937",
                accent_bg="#2d3748",
                secondary_bg="#111827",
                toggle_text="rgba(230, 150, 40, 170)",
                toggle_border="rgba(230, 150, 40, 170)",
                list_text="#e5e7eb",
            )
        )

    return (
        """
        QMainWindow {
            background: #f7f7fb;
        }
        QWidget#Sidebar {
            background: #ffffff;
            border-right: 1px solid #e6e6ef;
        }
        QLabel {
            color: #262730;
            font-weight: 600;
        }
        """
        + base.format(
            panel="#ffffff",
            border="#e6e6ef",
            text="#262730",
            muted="#444",
            header_bg="#f0f1f6",
            accent_bg="#ffe5e5",
            secondary_bg="#ffffff",
            toggle_text="rgba(200, 150, 40, 170)",
            toggle_border="rgba(200, 150, 40, 170)",
            list_text="#111111",
        )
    )


def main():
    app = QApplication(sys.argv)
    initial = "dark" if app.styleHints().colorScheme() == Qt.ColorScheme.Dark else "light"
    app.setStyleSheet(get_stylesheet(initial))
    window = MainWindow()
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
