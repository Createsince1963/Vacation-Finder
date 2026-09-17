"""Add/Edit dialog for a planned vacation, with a live working-days preview."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from calendar_logic import vacation_day_count
from models import Vacation


class VacationDialog(QDialog):
    def __init__(self, holiday_dates: set[str], vacation: Vacation | None = None, parent=None):
        super().__init__(parent)
        self._holiday_dates = holiday_dates
        self._editing = vacation

        self.setWindowTitle("Edit Vacation" if vacation else "Add Vacation")
        self.setMinimumWidth(360)

        self.name_edit = QLineEdit(vacation.name if vacation else "")
        self.name_edit.setPlaceholderText("Summer Trip")

        today = QDate.currentDate()
        self.start_edit = QDateEdit(calendar_popup=True)
        self.start_edit.setDate(
            QDate.fromString(vacation.start_date, "yyyy-MM-dd") if vacation else today
        )
        self.end_edit = QDateEdit(calendar_popup=True)
        self.end_edit.setDate(
            QDate.fromString(vacation.end_date, "yyyy-MM-dd") if vacation else today
        )

        self.half_day_check = QCheckBox("Half day (only when start = end date)")
        self.half_day_check.setChecked(bool(vacation.half_day) if vacation else False)
        self.half_day_check.setEnabled(self.start_edit.date() == self.end_edit.date())

        self.preview_label = QLabel()
        self.preview_label.setStyleSheet("color: #7c3aed; font-weight: bold;")

        form = QFormLayout()
        form.addRow("Vacation Name", self.name_edit)
        form.addRow("Start Date", self.start_edit)
        form.addRow("End Date", self.end_edit)
        form.addRow("", self.half_day_check)
        form.addRow("Working Days", self.preview_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self.start_edit.dateChanged.connect(self._update_preview)
        self.end_edit.dateChanged.connect(self._update_preview)
        self.half_day_check.stateChanged.connect(self._update_preview)
        self._update_preview()

        self.result_vacation: Vacation | None = None

    def _update_preview(self) -> None:
        start = self.start_edit.date().toString("yyyy-MM-dd")
        end = self.end_edit.date().toString("yyyy-MM-dd")

        same_day = self.start_edit.date() == self.end_edit.date()
        self.half_day_check.setEnabled(same_day)
        if not same_day:
            self.half_day_check.setChecked(False)

        count = vacation_day_count(start, end, self.half_day_check.isChecked(), self._holiday_dates)
        count_str = f"{count:g}"
        self.preview_label.setText(f"{count_str} working day(s) (excl. weekends & holidays)")

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setFocus()
            return
        start = self.start_edit.date().toString("yyyy-MM-dd")
        end = self.end_edit.date().toString("yyyy-MM-dd")
        if end < start:
            self.preview_label.setText("End date must not be before start date.")
            self.preview_label.setStyleSheet("color: #dc2626; font-weight: bold;")
            return

        from storage import new_vacation_id

        self.result_vacation = Vacation(
            id=self._editing.id if self._editing else new_vacation_id(),
            start_date=start,
            end_date=end,
            name=name,
            half_day=self.half_day_check.isChecked(),
        )
        self.accept()
