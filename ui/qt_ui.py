from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QListWidget,
    QStackedWidget,
    QTextEdit,
    QComboBox,
    QLineEdit,
    QCheckBox,
    QTableWidget,
    QTableView,
    QSpinBox,
    QGroupBox,
    QGridLayout,
    QHeaderView,
)


class UiMainWindow:
    def setup_ui(self, main_window):
        central = QWidget()
        root_layout = QHBoxLayout(central)

        self.sidebar = QWidget()
        self.sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setAlignment(Qt.AlignTop)

        self.btn_upload = QPushButton("Enviar SPED")
        self.lbl_file = QLabel("No file loaded")
        self.btn_save_current = QPushButton("Salvar Arquivo Atual")
        self.btn_save_current.setObjectName("SecondaryButton")
        self.btn_save_current.setEnabled(False)

        sidebar_layout.addWidget(self.btn_upload)
        sidebar_layout.addWidget(self.lbl_file)
        sidebar_layout.addWidget(self.btn_save_current)

        self.menu = QListWidget()
        self.menu.addItems(
            [
                "Visualizar Arquivo",
                "Alterar Campos",
                "Gerar Resumo",
                "Converter para Excel/CSV",
            ]
        )
        sidebar_layout.addWidget(self.menu)

        root_layout.addWidget(self.sidebar, 1)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_view_page())
        self.pages.addWidget(self._build_alter_page())
        self.pages.addWidget(self._build_summary_page())
        self.pages.addWidget(self._build_convert_page())
        root_layout.addWidget(self.pages, 4)

        main_window.setCentralWidget(central)

    def _build_view_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        header = QHBoxLayout()
        self.lbl_view_header = QLabel("Conteudo do arquivo (primeiras 100 linhas)")
        self.btn_theme_toggle = QPushButton("☾")
        self.btn_theme_toggle.setObjectName("ThemeToggle")
        self.btn_theme_toggle.setFlat(True)
        self.btn_theme_toggle.setFixedSize(18, 18)
        header.addWidget(self.lbl_view_header)
        header.addStretch(1)
        header.addWidget(self.btn_theme_toggle)

        self.view_text = QTextEdit()
        self.view_text.setReadOnly(True)
        layout.addLayout(header)
        layout.addWidget(self.view_text)
        return page

    def _build_alter_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(QLabel("1) Escolha o tipo de registro"))
        self.combo_registro = QComboBox()
        layout.addWidget(self.combo_registro)

        filtros_box = QGroupBox("2) Filtros (opcional)")
        filtros_layout = QGridLayout(filtros_box)
        self.filter_inputs = {}
        suggested_fields = ["CFOP", "CST_ICMS", "COD_ITEM", "NUM_DOC", "CHV_NFE", "CHV_CTE"]
        for row, field in enumerate(suggested_fields):
            lbl = QLabel(field)
            edit = QLineEdit()
            filtros_layout.addWidget(lbl, row, 0)
            filtros_layout.addWidget(edit, row, 1)
            self.filter_inputs[field] = (lbl, edit)
        self.edit_filtro_geral = QLineEdit()
        self.edit_filtro_geral.setPlaceholderText("Filtro geral por texto")
        filtros_layout.addWidget(QLabel("GERAL"), len(suggested_fields), 0)
        filtros_layout.addWidget(self.edit_filtro_geral, len(suggested_fields), 1)
        layout.addWidget(filtros_box)

        self.check_apply_all = QCheckBox("Aplicar alteracao em todos os filtrados")
        layout.addWidget(self.check_apply_all)

        layout.addWidget(QLabel("3) Registros filtrados"))
        self.check_select_all = QCheckBox("Selecionar todos desta pagina")
        layout.addWidget(self.check_select_all)

        self.table_lines = QTableWidget()
        self.table_lines.setColumnCount(2)
        self.table_lines.setHorizontalHeaderLabels(["Sel", "Linha"])
        self.table_lines.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.table_lines)

        page_controls = QHBoxLayout()
        page_controls.addWidget(QLabel("Pagina"))
        self.spin_page = QSpinBox()
        self.spin_page.setMinimum(1)
        page_controls.addWidget(self.spin_page)
        self.lbl_page_info = QLabel("0 items")
        page_controls.addWidget(self.lbl_page_info)
        layout.addLayout(page_controls)

        layout.addWidget(QLabel("4) Defina a alteracao"))
        self.combo_campo = QComboBox()
        self.edit_novo_valor = QLineEdit()
        layout.addWidget(self.combo_campo)
        layout.addWidget(self.edit_novo_valor)

        self.btn_apply = QPushButton("Aplicar alteracao")
        layout.addWidget(self.btn_apply)

        self.lbl_status = QLabel("")
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.btn_save_altered = QPushButton("Salvar Arquivo Alterado")
        self.btn_save_altered.setObjectName("SecondaryButton")
        self.btn_save_altered.setEnabled(False)
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.preview_text)
        layout.addWidget(self.btn_save_altered)
        return page

    def _build_summary_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        self.lbl_total_bc = QLabel("Total BC ICMS: -")
        self.lbl_total_icms = QLabel("Total ICMS: -")
        self.lbl_total_linhas = QLabel("Total linhas: -")
        layout.addWidget(self.lbl_total_bc)
        layout.addWidget(self.lbl_total_icms)
        layout.addWidget(self.lbl_total_linhas)

        layout.addWidget(QLabel("Resumo por CFOP"))
        self.view_cfop = QTableView()
        layout.addWidget(self.view_cfop)

        layout.addWidget(QLabel("Resumo por entrada/saida"))
        self.view_tipo = QTableView()
        layout.addWidget(self.view_tipo)
        return page

    def _build_convert_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.btn_export_excel = QPushButton("Exportar Excel (abas por registro)")
        self.btn_export_csv = QPushButton("Exportar CSV (ponto e virgula)")
        layout.addWidget(self.btn_export_excel)
        layout.addWidget(self.btn_export_csv)
        self.lbl_convert_status = QLabel("")
        layout.addWidget(self.lbl_convert_status)
        return page
