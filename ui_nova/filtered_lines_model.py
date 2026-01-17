from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex


class FilteredLinesModel(QAbstractTableModel):
    def __init__(self, linhas=None, selecionados=None):
        super().__init__()
        self._linhas = linhas or []  # list of (idx, line)
        self._selecionados = selecionados if selecionados is not None else set()

    def set_lines(self, linhas):
        self.beginResetModel()
        self._linhas = linhas
        self.endResetModel()

    def clear_selection(self):
        self._selecionados.clear()
        if self._linhas:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._linhas) - 1, 0),
                [Qt.CheckStateRole],
            )

    def select_all(self):
        self._selecionados = {idx for idx, _ in self._linhas}
        if self._linhas:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._linhas) - 1, 0),
                [Qt.CheckStateRole],
            )

    def selected_indices(self):
        return set(self._selecionados)

    def rowCount(self, parent=QModelIndex()):
        return len(self._linhas)

    def columnCount(self, parent=QModelIndex()):
        return 2

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        if row >= len(self._linhas):
            return None
        idx, line = self._linhas[row]
        if index.column() == 0 and role == Qt.CheckStateRole:
            return Qt.Checked if idx in self._selecionados else Qt.Unchecked
        if index.column() == 1 and role == Qt.DisplayRole:
            return line
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or index.column() != 0 or role != Qt.CheckStateRole:
            return False
        row = index.row()
        if row >= len(self._linhas):
            return False
        idx, _ = self._linhas[row]
        if value == Qt.Checked:
            self._selecionados.add(idx)
        else:
            self._selecionados.discard(idx)
        self.dataChanged.emit(index, index, [Qt.CheckStateRole])
        return True

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        if index.column() == 0:
            return Qt.ItemIsEnabled | Qt.ItemIsUserCheckable
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        if section == 0:
            return "Sel"
        return "Linha"
