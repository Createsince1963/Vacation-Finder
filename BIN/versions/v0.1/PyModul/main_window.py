"""Main application window: toolbar/filters, Year/Month/List views, exports."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import export
from api_client import holiday_applies_to_subdivision
from calendar_logic import (
    DEFAULT_MAX_BRIDGE_GAP,
    compute_bridge_days,
    format_date,
    generate_month_days,
    get_week_number,
    vacation_day_count,
    working_days_in_year,
)
from constants import APP_TITLE, COUNTRIES, COUNTRY_NAME_BY_CODE, YEARS
from entitlement import (
    YearBudget,
    YearEntitlement,
    compute_year_budget,
    get_year_entitlement,
    load_entitlement_settings,
    save_entitlement_settings,
)
from i18n import SUPPORTED_LANGUAGES, month_names, tr
from models import CalendarDay, Holiday, SchoolHoliday, Subdivision, Vacation
from storage import load_vacations, save_vacations
from user_config import UserConfig, load_user_config, save_user_config
from vacation_dialog import VacationDialog
from workers import start_holiday_fetch

# From September onward, silently prefetch next year's holiday data in the
# background so it is already cached by the time the automatic year
# rollover happens on Jan 1 (see _check_year_rollover_and_prefetch).
PREFETCH_START_MONTH = 9
# How often to check for a real-world year rollover / whether it is time
# to prefetch next year's data. The app does not need to react within
# seconds of midnight, so a low-frequency timer is fine and cheap.
ROLLOVER_CHECK_INTERVAL_MS = 60 * 60 * 1000  # 1 hour

WEEKDAY_SHORT = ["M", "T", "W", "T", "F", "S", "S"]

COLOR_HOLIDAY = QColor("#dbeafe")
COLOR_BRIDGE = QColor("#dcfce7")
COLOR_VACATION = QColor("#f3e8ff")
COLOR_SCHOOL = QColor("#fef9c3")
COLOR_WEEKEND = QColor("#fff7ed")
# Search-term highlighting (applied on top of the category colors above):
# a day matching the search box is highlighted, everything else is dimmed,
# so the search box actually has a visible effect on the calendar views
# instead of just sitting there (previously a known v1 gap).
COLOR_SEARCH_MATCH = QColor("#fde047")
COLOR_SEARCH_DIM = QColor("#f3f4f6")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1200, 800)

        # --- state -------------------------------------------------------
        self.user_config: UserConfig = load_user_config()
        self.language = self.user_config.language

        self.selected_country = "DE"
        self.selected_country2: str | None = None
        self.selected_subdivision: str | None = None
        self.selected_year = date.today().year
        self.selected_month = date.today().month  # 1-12
        self.source = "nager"
        self.view_mode = "month"

        self.holidays: list[Holiday] = []
        self.school_holidays: list[SchoolHoliday] = []
        self.subdivisions: list[Subdivision] = []
        self.vacations: list[Vacation] = load_vacations()

        # Multi-year cache: once a year's holidays have been fetched (either
        # because the user selected it, or via the September-onward
        # background prefetch below), they stay available here so year
        # rollover and carryover/budget math don't need a network round
        # trip every time.
        self.holidays_by_year: dict[int, list[Holiday]] = {}
        self.school_holidays_by_year: dict[int, list[SchoolHoliday]] = {}

        self.entitlement_settings: dict[int, YearEntitlement] = load_entitlement_settings()

        self.max_bridge_gap = DEFAULT_MAX_BRIDGE_GAP
        self.bridge_dates_primary: set[str] = set()
        self.bridge_dates_secondary: set[str] = set()

        self.show_holidays = True
        self.show_bridge_days = True
        self.show_weekends = True
        self.show_vacations = True
        self.show_school_holidays = False
        self.search_term = ""

        self._fetch_thread = None
        self._fetch_worker = None
        self._prefetch_thread = None
        self._prefetch_worker = None
        self._last_known_today = date.today()
        # True while selected_year tracks "whatever the real-world current
        # year is" (the normal, default state). Set to False the moment the
        # user explicitly picks a different year, so the automatic Jan-1
        # rollover never yanks them away from a year they chose on purpose.
        self._year_follows_today = True

        self._build_ui()
        self._render_vacations_panel()
        self._render_budget_panel()
        self.refresh_data()

        self._rollover_timer = QTimer(self)
        self._rollover_timer.setInterval(ROLLOVER_CHECK_INTERVAL_MS)
        self._rollover_timer.timeout.connect(self._check_year_rollover_and_prefetch)
        self._rollover_timer.start()
        # Also run once at startup (covers: app opened for the first time
        # after Jan 1, or opened in September+ with no prefetch cached yet).
        self._check_year_rollover_and_prefetch()

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------
    def _tr(self, key: str) -> str:
        return tr(key, self.language)

    def _month_names(self) -> list[str]:
        return month_names(self.language)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        root.addLayout(self._build_toolbar())
        root.addLayout(self._build_filter_bar())
        root.addWidget(self._build_budget_panel())
        root.addWidget(self._build_vacations_panel())

        self.stack = QStackedWidget()
        self.year_page = self._build_year_page()
        self.month_page = self._build_month_page()
        self.list_page = self._build_list_page()
        self.stack.addWidget(self.year_page)
        self.stack.addWidget(self.month_page)
        self.stack.addWidget(self.list_page)
        root.addWidget(self.stack, stretch=1)

        self.setStatusBar(QStatusBar())

    def _build_toolbar(self) -> QHBoxLayout:
        row = QHBoxLayout()

        self._label_country = QLabel(self._tr("toolbar_country"))
        row.addWidget(self._label_country)
        self.country_combo = QComboBox()
        for c in COUNTRIES:
            self.country_combo.addItem(c["name"], c["code"])
        self.country_combo.setCurrentIndex(
            [c["code"] for c in COUNTRIES].index(self.selected_country)
        )
        self.country_combo.currentIndexChanged.connect(self._on_country_changed)
        row.addWidget(self.country_combo)

        self._label_state = QLabel(self._tr("toolbar_state"))
        row.addWidget(self._label_state)
        self.subdivision_combo = QComboBox()
        self.subdivision_combo.addItem("All States", None)
        self.subdivision_combo.currentIndexChanged.connect(self._on_subdivision_changed)
        row.addWidget(self.subdivision_combo)

        self._label_compare_with = QLabel(self._tr("toolbar_compare_with"))
        row.addWidget(self._label_compare_with)
        self.country2_combo = QComboBox()
        self.country2_combo.addItem("None", None)
        for c in COUNTRIES:
            self.country2_combo.addItem(c["name"], c["code"])
        self.country2_combo.currentIndexChanged.connect(self._on_country2_changed)
        row.addWidget(self.country2_combo)

        self._label_year = QLabel(self._tr("toolbar_year"))
        row.addWidget(self._label_year)
        self.year_combo = QComboBox()
        for y in YEARS:
            self.year_combo.addItem(str(y), y)
        self.year_combo.setCurrentIndex(YEARS.index(self.selected_year) if self.selected_year in YEARS else 0)
        self.year_combo.currentIndexChanged.connect(self._on_year_changed)
        row.addWidget(self.year_combo)

        self.source_button = QPushButton("Source: Nager.Date")
        self.source_button.clicked.connect(self._toggle_source)
        row.addWidget(self.source_button)

        self._label_bridge_gap = QLabel(self._tr("toolbar_max_bridge_gap"))
        row.addWidget(self._label_bridge_gap)
        self.bridge_gap_spin = QSpinBox()
        self.bridge_gap_spin.setRange(1, 3)
        self.bridge_gap_spin.setValue(self.max_bridge_gap)
        self.bridge_gap_spin.setSuffix(" day(s)")
        self.bridge_gap_spin.setToolTip(
            "How many consecutive working days between two non-working days "
            "(weekend/holiday) still count as a worthwhile bridge day. "
            "Lower = only single-day gaps; higher = also flags 2-3 day gaps."
        )
        self.bridge_gap_spin.valueChanged.connect(self._on_bridge_gap_changed)
        row.addWidget(self.bridge_gap_spin)

        self._label_language = QLabel(self._tr("toolbar_language"))
        row.addWidget(self._label_language)
        self.language_combo = QComboBox()
        for code, native_name in SUPPORTED_LANGUAGES:
            self.language_combo.addItem(native_name, code)
        self.language_combo.setCurrentIndex(
            [c for c, _ in SUPPORTED_LANGUAGES].index(self.language)
            if self.language in [c for c, _ in SUPPORTED_LANGUAGES]
            else 0
        )
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        row.addWidget(self.language_combo)

        row.addStretch(1)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self._tr("toolbar_search_placeholder"))
        self.search_edit.textChanged.connect(self._on_search_changed)
        row.addWidget(self.search_edit)

        self.today_btn = QPushButton(self._tr("toolbar_today"))
        self.today_btn.clicked.connect(self._go_to_today)
        row.addWidget(self.today_btn)

        return row

    def _build_filter_bar(self) -> QHBoxLayout:
        row = QHBoxLayout()

        for key, attr in [
            ("view_year", "year"), ("view_month", "month"), ("view_list", "list"),
        ]:
            btn = QToolButton()
            btn.setText(self._tr(key))
            btn.setCheckable(True)
            btn.setChecked(attr == self.view_mode)
            btn.clicked.connect(lambda _checked, mode=attr: self._set_view_mode(mode))
            row.addWidget(btn)
            setattr(self, f"_view_btn_{attr}", btn)

        row.addSpacing(20)

        self.chk_holidays = QCheckBox(self._tr("filter_holidays"))
        self.chk_holidays.setChecked(self.show_holidays)
        self.chk_bridge = QCheckBox(self._tr("filter_bridge_days"))
        self.chk_bridge.setChecked(self.show_bridge_days)
        self.chk_weekends = QCheckBox(self._tr("filter_weekends"))
        self.chk_weekends.setChecked(self.show_weekends)
        self.chk_vacations = QCheckBox(self._tr("filter_vacations"))
        self.chk_vacations.setChecked(self.show_vacations)
        self.chk_school = QCheckBox(self._tr("filter_school"))
        self.chk_school.setChecked(self.show_school_holidays)

        for chk in (
            self.chk_holidays, self.chk_bridge, self.chk_weekends,
            self.chk_vacations, self.chk_school,
        ):
            chk.stateChanged.connect(self._on_filters_changed)
            row.addWidget(chk)

        row.addStretch(1)

        self.export_excel_btn = QPushButton(self._tr("btn_export_excel"))
        self.export_excel_btn.clicked.connect(self._export_excel)
        row.addWidget(self.export_excel_btn)

        self.export_ical_btn = QPushButton(self._tr("btn_export_ical"))
        self.export_ical_btn.clicked.connect(self._export_ical)
        row.addWidget(self.export_ical_btn)

        self.add_vacation_btn = QPushButton(self._tr("btn_add_vacation"))
        self.add_vacation_btn.clicked.connect(self._add_vacation)
        row.addWidget(self.add_vacation_btn)

        return row

    def _build_year_page(self) -> QWidget:
        page = QWidget()
        self.year_grid = QGridLayout(page)
        return page

    def _build_month_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        nav = QHBoxLayout()
        prev_btn = QPushButton("<")
        prev_btn.clicked.connect(self._prev_month)
        next_btn = QPushButton(">")
        next_btn.clicked.connect(self._next_month)
        self.month_title_label = QLabel()
        self.month_title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        nav.addWidget(prev_btn)
        nav.addWidget(self.month_title_label, stretch=1)
        nav.addWidget(next_btn)
        layout.addLayout(nav)

        self.month_table = QTableWidget(0, 4)
        self.month_table.setHorizontalHeaderLabels(
            [self._tr("month_col_kw"), self._tr("month_col_weekday"),
             self._tr("month_col_date"), self._tr("month_col_description")]
        )
        self.month_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.month_table.verticalHeader().setVisible(False)
        self.month_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.month_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        layout.addWidget(self.month_table)

        return page

    def _build_list_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.list_count_label = QLabel()
        layout.addWidget(self.list_count_label)

        self.list_table = QTableWidget(0, 6)
        self.list_table.setHorizontalHeaderLabels(
            [self._tr("list_col_date"), self._tr("list_col_weekday"), self._tr("list_col_type"),
             self._tr("list_col_country"), self._tr("list_col_description"), self._tr("list_col_kw")]
        )
        self.list_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.list_table.verticalHeader().setVisible(False)
        self.list_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.list_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.list_table.setSortingEnabled(True)
        layout.addWidget(self.list_table)

        return page

    def _build_vacations_panel(self) -> QGroupBox:
        box = QGroupBox(self._tr("panel_planned_vacations"))
        self.vacations_group_box = box
        layout = QVBoxLayout(box)

        header = QHBoxLayout()
        self.vacations_total_label = QLabel()
        header.addWidget(self.vacations_total_label)
        header.addStretch(1)
        layout.addLayout(header)

        self.vacations_table = QTableWidget(0, 4)
        self.vacations_table.setHorizontalHeaderLabels(
            [self._tr("vac_col_name"), self._tr("vac_col_date_range"), self._tr("vac_col_working_days"), ""]
        )
        self.vacations_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.vacations_table.verticalHeader().setVisible(False)
        self.vacations_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.vacations_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.vacations_table.setMaximumHeight(180)
        layout.addWidget(self.vacations_table)

        box.setVisible(False)
        self.vacations_panel = box
        return box

    def _render_vacations_panel(self) -> None:
        self.vacations_panel.setVisible(len(self.vacations) > 0)
        holiday_dates = self._holiday_dates(self.selected_country)

        total_days = 0.0
        self.vacations_table.setRowCount(len(self.vacations))
        for row, v in enumerate(sorted(self.vacations, key=lambda x: x.start_date)):
            working_days = vacation_day_count(v.start_date, v.end_date, v.half_day, holiday_dates)
            total_days += working_days

            self.vacations_table.setItem(row, 0, QTableWidgetItem(v.name))
            self.vacations_table.setItem(
                row, 1, QTableWidgetItem(f"{v.start_date} - {v.end_date}")
            )
            self.vacations_table.setItem(
                row, 2, QTableWidgetItem(f"{working_days:g} {self._tr('label_days_unit')}")
            )

            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            edit_btn = QPushButton(self._tr("btn_edit"))
            edit_btn.clicked.connect(lambda _checked, vac=v: self._edit_vacation(vac))
            remove_btn = QPushButton(self._tr("btn_remove"))
            remove_btn.clicked.connect(lambda _checked, vac=v: self._remove_vacation(vac))
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(remove_btn)
            self.vacations_table.setCellWidget(row, 3, actions)

        # The old hardcoded ">30 days" warning is gone - the Vacation Budget
        # panel above now shows the real entitlement-based remaining balance
        # (base days + overtime bonus + carryover, minus days actually used
        # in the selected year). This total is simply "all planned vacations
        # across every year", kept as a quick at-a-glance figure.
        self.vacations_total_label.setText(
            f"{self._tr('vac_total_planned')}: {total_days:g} {self._tr('label_working_days_unit')}"
        )
        self.vacations_total_label.setStyleSheet("font-weight: bold;")

    # ------------------------------------------------------------------
    # Vacation budget (annual entitlement, overtime bonus days, carryover)
    # ------------------------------------------------------------------
    def _build_budget_panel(self) -> QGroupBox:
        box = QGroupBox(self._tr("panel_vacation_budget"))
        self.budget_group_box = box
        layout = QGridLayout(box)

        self._label_base_days = QLabel(self._tr("budget_base_days"))
        layout.addWidget(self._label_base_days, 0, 0)
        self.base_days_spin = QDoubleSpinBox()
        self.base_days_spin.setRange(0, 366)
        self.base_days_spin.setDecimals(1)
        self.base_days_spin.setSingleStep(0.5)
        self.base_days_spin.valueChanged.connect(self._on_entitlement_field_changed)
        layout.addWidget(self.base_days_spin, 0, 1)

        self._label_overtime_hours = QLabel(self._tr("budget_overtime_hours"))
        layout.addWidget(self._label_overtime_hours, 0, 2)
        self.overtime_hours_spin = QDoubleSpinBox()
        self.overtime_hours_spin.setRange(0, 2000)
        self.overtime_hours_spin.setDecimals(1)
        self.overtime_hours_spin.setSingleStep(1.0)
        self.overtime_hours_spin.setToolTip(
            "Banked overtime hours. Converted to extra flex/bridge days below "
            "using 'Hours/day'."
        )
        self.overtime_hours_spin.valueChanged.connect(self._on_entitlement_field_changed)
        layout.addWidget(self.overtime_hours_spin, 0, 3)

        self._label_hours_per_day = QLabel(self._tr("budget_hours_per_day"))
        layout.addWidget(self._label_hours_per_day, 0, 4)
        self.hours_per_day_spin = QDoubleSpinBox()
        self.hours_per_day_spin.setRange(1, 24)
        self.hours_per_day_spin.setDecimals(1)
        self.hours_per_day_spin.setSingleStep(0.5)
        self.hours_per_day_spin.valueChanged.connect(self._on_entitlement_field_changed)
        layout.addWidget(self.hours_per_day_spin, 0, 5)

        self.budget_summary_label = QLabel()
        self.budget_summary_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.budget_summary_label, 1, 0, 1, 6)

        self.budget_panel = box
        return box

    def _on_entitlement_field_changed(self, _value: float) -> None:
        self._save_current_year_entitlement()
        self._render_vacations_panel()
        self._render_budget_panel()

    def _save_current_year_entitlement(self) -> None:
        existing = get_year_entitlement(self.entitlement_settings, self.selected_year)
        self.entitlement_settings[self.selected_year] = YearEntitlement(
            base_days=self.base_days_spin.value(),
            overtime_hours=self.overtime_hours_spin.value(),
            hours_per_day=self.hours_per_day_spin.value(),
            carryover_override=existing.carryover_override,
        )
        save_entitlement_settings(self.entitlement_settings)

    def _used_days_for_year(self, year: int) -> float:
        """Sum of vacation working days that fall within `year`, using that
        year's own holiday calendar when it's cached (falls back to no
        holiday exclusions if that year hasn't been fetched yet - a rare
        edge case, e.g. computing carryover from a year the app never
        loaded holidays for)."""
        holiday_dates = {h.date for h in self.holidays_by_year.get(year, [])}
        return sum(
            working_days_in_year(v.start_date, v.end_date, v.half_day, holiday_dates, year)
            for v in self.vacations
        )

    def _compute_budget_for_year(self, year: int) -> YearBudget:
        """Budget for `year`, including carryover from `year - 1`.

        Deliberately only looks one year back: the previous year's own
        carryover-in is treated as 0 here rather than recursing further,
        since the feature this serves ("Resttage ins naechste Jahr
        uebernehmen") is about one rollover at a time, not an indefinite
        chain, and unresolved multi-year chains would let unused days
        silently accumulate forever.
        """
        prev_year = year - 1
        prev_budget: YearBudget | None = None
        # Only compute a carryover if the user has actually configured
        # (or used) the previous year - otherwise every year would show a
        # phantom "30 days carried over" from an imaginary, never-touched
        # previous year (YearEntitlement()'s own default base_days=30),
        # which would silently inflate the very first year's budget.
        if prev_year in self.entitlement_settings or any(
            v.start_date.startswith(f"{prev_year}-") or v.end_date.startswith(f"{prev_year}-")
            for v in self.vacations
        ):
            prev_entitlement = get_year_entitlement(self.entitlement_settings, prev_year)
            prev_budget = YearBudget(
                base_days=prev_entitlement.base_days,
                overtime_bonus_days=prev_entitlement.overtime_bonus_days,
                carryover_from_previous_year=0.0,
                used_days=self._used_days_for_year(prev_year),
            )
        return compute_year_budget(
            self.entitlement_settings,
            year,
            used_days=self._used_days_for_year(year),
            previous_year_budget=prev_budget,
        )

    def _render_budget_panel(self) -> None:
        entitlement = get_year_entitlement(self.entitlement_settings, self.selected_year)
        for spin, value in (
            (self.base_days_spin, entitlement.base_days),
            (self.overtime_hours_spin, entitlement.overtime_hours),
            (self.hours_per_day_spin, entitlement.hours_per_day),
        ):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)

        budget = self._compute_budget_for_year(self.selected_year)
        summary = (
            f"{self.selected_year}: {budget.total_available:g} {self._tr('budget_available')} "
            f"({budget.base_days:g} {self._tr('budget_base_word')} + {budget.overtime_bonus_days:g} "
            f"{self._tr('budget_from_overtime')} + {budget.carryover_from_previous_year:g} "
            f"{self._tr('budget_carried_over')})  |  "
            f"{self._tr('budget_used')}: {budget.used_days:g}  |  "
            f"{self._tr('budget_remaining')}: {budget.remaining:g}"
        )
        self.budget_summary_label.setText(summary)
        self.budget_summary_label.setStyleSheet(
            "color: #c2410c; font-weight: bold;" if budget.remaining < 0 else "font-weight: bold;"
        )

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def refresh_data(self) -> None:
        self.statusBar().showMessage("Synchronizing global data...")
        self._fetch_thread, self._fetch_worker = start_holiday_fetch(
            self,
            self.selected_country,
            self.selected_country2,
            self.selected_year,
            self.source,
            self.selected_subdivision,
            fetch_subdivisions=True,
            on_finished=self._on_data_loaded,
            on_failed=self._on_data_failed,
        )
        # thread.deleteLater() (wired inside start_holiday_fetch) destroys the
        # underlying C++ QThread once the fetch is done. Drop our Python
        # reference at the same point so a later closeEvent/refresh never
        # touches an already-deleted QThread (RuntimeError from shiboken).
        self._fetch_thread.finished.connect(self._clear_fetch_thread_ref)

    def _clear_fetch_thread_ref(self) -> None:
        self._fetch_thread = None
        self._fetch_worker = None

    def _on_data_loaded(
        self,
        holidays: list[Holiday],
        school_holidays: list[SchoolHoliday],
        subdivisions: list[Subdivision],
    ) -> None:
        self.holidays = holidays
        self.school_holidays = school_holidays
        # Cache this year's holidays so budget/carryover math and the
        # rollover check don't need to re-fetch data that's already here.
        self.holidays_by_year[self.selected_year] = holidays
        self.school_holidays_by_year[self.selected_year] = school_holidays
        if subdivisions:
            self.subdivisions = subdivisions
            self._populate_subdivisions()
        self._recompute_bridge_days()
        self._render_vacations_panel()
        self._render_budget_panel()
        self.statusBar().showMessage(self._tr("status_ready"), 3000)
        self._rebuild_current_view()

    def _recompute_bridge_days(self) -> None:
        self.bridge_dates_primary = compute_bridge_days(
            self.selected_year, self._holiday_dates(self.selected_country), self.max_bridge_gap
        )
        self.bridge_dates_secondary = (
            compute_bridge_days(
                self.selected_year,
                self._holiday_dates(self.selected_country2),
                self.max_bridge_gap,
            )
            if self.selected_country2
            else set()
        )

    def _on_bridge_gap_changed(self, value: int) -> None:
        self.max_bridge_gap = value
        self._recompute_bridge_days()
        self._rebuild_current_view()

    def _on_data_failed(self, message: str) -> None:
        self.statusBar().showMessage(f"Error loading data: {message}", 6000)
        self._rebuild_current_view()

    def _populate_subdivisions(self) -> None:
        self.subdivision_combo.blockSignals(True)
        self.subdivision_combo.clear()
        self.subdivision_combo.addItem("All States", None)
        for s in self.subdivisions:
            self.subdivision_combo.addItem(s.name, s.code)
        self.subdivision_combo.blockSignals(False)

    # ------------------------------------------------------------------
    # Automatic year rollover (Jan 1) + September-onward next-year prefetch
    # ------------------------------------------------------------------
    def _check_year_rollover_and_prefetch(self) -> None:
        today = date.today()

        # 1) Rollover: if the real-world year has advanced since we last
        # checked, and the user hasn't manually pinned a different year,
        # follow it - e.g. the app is left running (or is simply opened
        # again) after midnight on Jan 1.
        if today.year > self._last_known_today.year and self._year_follows_today:
            self.selected_year = today.year
            self.selected_month = today.month
            if today.year in YEARS:
                self.year_combo.blockSignals(True)
                self.year_combo.setCurrentIndex(YEARS.index(today.year))
                self.year_combo.blockSignals(False)
            self.refresh_data()
        self._last_known_today = today

        # 2) Prefetch: from September onward, make sure next year's holiday
        # data is already cached before it's needed, so the Jan 1 rollover
        # above (or the user picking next year from the combo) doesn't have
        # to wait on the network.
        if today.month >= PREFETCH_START_MONTH:
            next_year = today.year + 1
            if next_year not in self.holidays_by_year and self._prefetch_thread is None:
                self._start_prefetch_next_year(next_year)

    def _start_prefetch_next_year(self, year: int) -> None:
        self._prefetch_thread, self._prefetch_worker = start_holiday_fetch(
            self,
            self.selected_country,
            None,  # no comparison country needed just to warm the cache
            year,
            self.source,
            None,  # nationwide only for the cache; subdivision filtering is client-side anyway
            fetch_subdivisions=False,
            on_finished=lambda h, sh, _subs, y=year: self._on_prefetch_finished(y, h, sh),
            on_failed=self._on_prefetch_failed,
        )
        self._prefetch_thread.finished.connect(self._clear_prefetch_thread_ref)

    def _clear_prefetch_thread_ref(self) -> None:
        self._prefetch_thread = None
        self._prefetch_worker = None

    def _on_prefetch_finished(
        self, year: int, holidays: list[Holiday], school_holidays: list[SchoolHoliday]
    ) -> None:
        self.holidays_by_year[year] = holidays
        self.school_holidays_by_year[year] = school_holidays
        # Only affects the display if the user happens to already be
        # looking at that (upcoming) year's budget/carryover figures.
        if self.selected_year in (year, year + 1):
            self._render_budget_panel()

    def _on_prefetch_failed(self, _message: str) -> None:
        # Silent by design - this is a background warm-up, not a
        # user-initiated action. It will simply be retried on the next
        # rollover-check tick (still not cached, still >= September).
        pass

    # ------------------------------------------------------------------
    # Derived data helpers
    # ------------------------------------------------------------------
    def _visible_holidays(self) -> list[Holiday]:
        """self.holidays filtered by the selected Bundesland/Kanton (if any).

        Nager.Date and OpenHolidays only let us fetch holidays per country,
        not per subdivision - each holiday carries its own scope
        (nationwide, or a list of subdivision codes). This applies that
        scope client-side, but only to the primary country: the
        comparison country has no subdivision selector in this UI.
        """
        if not self.selected_subdivision:
            return self.holidays
        return [
            h
            for h in self.holidays
            if h.country_code != self.selected_country
            or holiday_applies_to_subdivision(h, self.selected_subdivision)
        ]

    def _holiday_dates(self, country_code: str) -> set[str]:
        return {h.date for h in self._visible_holidays() if h.country_code == country_code}

    def _generate_month(self, year: int, month: int) -> list[CalendarDay]:
        # Bridge-day sets are precomputed for the whole selected_year in
        # _recompute_bridge_days(); if a different year is requested here
        # (should not normally happen), recompute on the fly rather than
        # silently using stale/mismatched data.
        bridge_primary = (
            self.bridge_dates_primary
            if year == self.selected_year
            else compute_bridge_days(year, self._holiday_dates(self.selected_country), self.max_bridge_gap)
        )
        bridge_secondary = (
            self.bridge_dates_secondary
            if year == self.selected_year
            else (
                compute_bridge_days(year, self._holiday_dates(self.selected_country2), self.max_bridge_gap)
                if self.selected_country2
                else set()
            )
        )
        return generate_month_days(
            year,
            month,
            self._visible_holidays(),
            bridge_primary,
            bridge_secondary,
            self.selected_country,
            self.selected_country2,
            self.vacations,
            self.school_holidays,
        )

    def _generate_year(self, year: int) -> list[CalendarDay]:
        days: list[CalendarDay] = []
        for m in range(1, 13):
            days.extend(self._generate_month(year, m))
        return days

    def _day_passes_filters(self, day: CalendarDay) -> bool:
        if day.is_holiday and self.show_holidays:
            return True
        if day.is_bridge_day and self.show_bridge_days:
            return True
        if day.is_vacation and self.show_vacations:
            return True
        if day.is_school_holiday and self.show_school_holidays:
            return True
        if day.is_weekend and self.show_weekends:
            return True
        return False

    def _day_matches_search(self, day: CalendarDay) -> bool:
        """True if `day` matches the search box (always true when it's empty)."""
        term = self.search_term.strip().lower()
        if not term:
            return True
        candidates: list[str] = []
        if day.holiday_name:
            candidates.append(day.holiday_name)
        if day.vacation_name:
            candidates.append(day.vacation_name)
        if day.school_holiday_name:
            candidates.append(day.school_holiday_name)
        if day.is_bridge_day:
            candidates.append(self._tr("day_type_bridge_day"))
            candidates.extend(day.bridge_day_countries)
        if day.is_weekend:
            candidates.append(self._tr("day_type_weekend"))
        return any(term in c.lower() for c in candidates)

    # ------------------------------------------------------------------
    # View rendering
    # ------------------------------------------------------------------
    def _rebuild_current_view(self) -> None:
        if self.view_mode == "year":
            self._render_year_view()
        elif self.view_mode == "month":
            self._render_month_view()
        else:
            self._render_list_view()

    def _render_year_view(self) -> None:
        while self.year_grid.count():
            item = self.year_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        month_names = self._month_names()
        for m in range(1, 13):
            box = QGroupBox(f"{month_names[m - 1]} (Q{(m - 1) // 3 + 1})")
            box_layout = QVBoxLayout(box)
            table = QTableWidget(6, 8)
            table.setHorizontalHeaderLabels(["KW"] + WEEKDAY_SHORT)
            table.verticalHeader().setVisible(False)
            table.horizontalHeader().setVisible(True)
            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

            days = self._generate_month(self.selected_year, m)
            first_weekday = date(self.selected_year, m, 1).weekday()  # Monday=0

            row, col = 0, first_weekday
            if col == 0 and row == 0:
                pass
            table.setItem(0, 0, QTableWidgetItem(str(days[0].week_number if days else "")))
            for day in days:
                if col == 0:
                    table.setItem(row, 0, QTableWidgetItem(str(day.week_number)))
                item = QTableWidgetItem(str(day.date.day))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                color = self._row_background(day)
                if color:
                    item.setBackground(color)
                table.setItem(row, col + 1, item)
                col += 1
                if col > 6:
                    col = 0
                    row += 1
                    if row >= table.rowCount():
                        table.insertRow(table.rowCount())

            table.setFixedHeight(28 * (table.rowCount() + 1))
            box_layout.addWidget(table)
            self.year_grid.addWidget(box, (m - 1) // 4, (m - 1) % 4)

    def _day_color(self, day: CalendarDay) -> QColor | None:
        if day.is_holiday and self.show_holidays:
            return COLOR_HOLIDAY
        if day.is_bridge_day and self.show_bridge_days:
            return COLOR_BRIDGE
        if day.is_vacation and self.show_vacations:
            return COLOR_VACATION
        if day.is_school_holiday and self.show_school_holidays:
            return COLOR_SCHOOL
        if day.is_weekend and self.show_weekends:
            return COLOR_WEEKEND
        return None

    def _row_background(self, day: CalendarDay) -> QColor | None:
        """Category color, composed with search-term highlighting: while a
        search is active, a matching day is highlighted and everything
        else is dimmed, so the search box has a visible effect on every
        calendar view (Year/Month/List)."""
        if self.search_term.strip():
            return COLOR_SEARCH_MATCH if self._day_matches_search(day) else COLOR_SEARCH_DIM
        return self._day_color(day)

    def _render_month_view(self) -> None:
        month_names = self._month_names()
        self.month_title_label.setText(f"{month_names[self.selected_month - 1]} {self.selected_year}")
        days = self._generate_month(self.selected_year, self.selected_month)

        self.month_table.setRowCount(len(days))
        for row, day in enumerate(days):
            weekday_name = day.date.strftime("%A")
            self.month_table.setItem(row, 0, QTableWidgetItem(f"{self._tr('month_col_kw')} {day.week_number}"))
            self.month_table.setItem(row, 1, QTableWidgetItem(weekday_name))
            self.month_table.setItem(row, 2, QTableWidgetItem(day.date.strftime("%d.%m.%Y")))

            if day.is_holiday and self.show_holidays:
                desc = day.holiday_name or ""
            elif day.is_vacation and self.show_vacations:
                desc = f"{day.vacation_name} ({self._tr('desc_personal_vacation')})"
            elif day.is_bridge_day and self.show_bridge_days:
                desc = self._tr("desc_strategic_bridge_day") + " (" + ", ".join(day.bridge_day_countries) + ")"
            elif day.is_weekend and self.show_weekends:
                desc = self._tr("day_type_weekend")
            else:
                desc = self._tr("desc_standard_business_day")
            self.month_table.setItem(row, 3, QTableWidgetItem(desc))

            color = self._row_background(day)
            if color:
                for col in range(4):
                    self.month_table.item(row, col).setBackground(color)

    def _render_list_view(self) -> None:
        days = self._generate_year(self.selected_year)
        filtered = [
            d for d in days if self._day_passes_filters(d) and self._day_matches_search(d)
        ]
        filtered.sort(key=lambda d: d.date)

        self.list_count_label.setText(f"{len(filtered)} {self._tr('list_days_found')}")
        self.list_table.setSortingEnabled(False)
        self.list_table.setRowCount(len(filtered))
        for row, day in enumerate(filtered):
            day_type = (
                self._tr("day_type_holiday") if day.is_holiday else
                self._tr("day_type_vacation") if day.is_vacation else
                self._tr("day_type_bridge_day") if day.is_bridge_day else
                self._tr("day_type_school_holiday") if day.is_school_holiday else
                self._tr("day_type_weekend")
            )
            countries = (
                ", ".join(h.country_code for h in day.holidays) if day.is_holiday and day.holidays
                else ", ".join(day.bridge_day_countries) if day.is_bridge_day
                else "-"
            )
            description = (
                day.holiday_name or day.vacation_name or day.school_holiday_name
                or (self._tr("desc_strategic_bridge_day") if day.is_bridge_day else self._tr("day_type_weekend"))
            )

            self.list_table.setItem(row, 0, QTableWidgetItem(day.date.strftime("%d.%m.%Y")))
            self.list_table.setItem(row, 1, QTableWidgetItem(day.date.strftime("%A")))
            self.list_table.setItem(row, 2, QTableWidgetItem(day_type))
            self.list_table.setItem(row, 3, QTableWidgetItem(countries))
            self.list_table.setItem(row, 4, QTableWidgetItem(description))
            self.list_table.setItem(row, 5, QTableWidgetItem(str(day.week_number)))

            # In list view, everything shown already passed the search
            # filter above, so category color takes priority here (no dim
            # state needed - there's nothing non-matching left to dim).
            color = self._day_color(day)
            if color:
                for col in range(6):
                    self.list_table.item(row, col).setBackground(color)
        self.list_table.setSortingEnabled(True)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _on_country_changed(self) -> None:
        self.selected_country = self.country_combo.currentData()
        self.selected_subdivision = None
        self.refresh_data()

    def _on_subdivision_changed(self) -> None:
        self.selected_subdivision = self.subdivision_combo.currentData()
        self.refresh_data()

    def _on_country2_changed(self) -> None:
        self.selected_country2 = self.country2_combo.currentData()
        self.refresh_data()

    def _on_year_changed(self) -> None:
        self.selected_year = self.year_combo.currentData()
        # The user just picked a year explicitly - stop auto-following the
        # real-world "current year" until they go back to Today, so the
        # Jan 1 rollover never yanks them away from a year they chose.
        self._year_follows_today = self.selected_year == date.today().year
        self.refresh_data()

    def _toggle_source(self) -> None:
        self.source = "openholidays" if self.source == "nager" else "nager"
        self.source_button.setText(
            "Source: OpenHolidays" if self.source == "openholidays" else "Source: Nager.Date"
        )
        self.refresh_data()

    def _on_search_changed(self, text: str) -> None:
        self.search_term = text
        self._rebuild_current_view()

    def _on_language_changed(self) -> None:
        self.language = self.language_combo.currentData()
        self.user_config = UserConfig(language=self.language)
        save_user_config(self.user_config)
        self._retranslate_ui()

    def _retranslate_ui(self) -> None:
        """Update every static widget's text to the newly selected
        language, then re-render the dynamic panels/views (their text is
        built fresh each render, so they pick up the new language too)."""
        self._label_country.setText(self._tr("toolbar_country"))
        self._label_state.setText(self._tr("toolbar_state"))
        self._label_compare_with.setText(self._tr("toolbar_compare_with"))
        self._label_year.setText(self._tr("toolbar_year"))
        self._label_bridge_gap.setText(self._tr("toolbar_max_bridge_gap"))
        self._label_language.setText(self._tr("toolbar_language"))
        self.search_edit.setPlaceholderText(self._tr("toolbar_search_placeholder"))
        self.today_btn.setText(self._tr("toolbar_today"))

        self._view_btn_year.setText(self._tr("view_year"))
        self._view_btn_month.setText(self._tr("view_month"))
        self._view_btn_list.setText(self._tr("view_list"))

        self.chk_holidays.setText(self._tr("filter_holidays"))
        self.chk_bridge.setText(self._tr("filter_bridge_days"))
        self.chk_weekends.setText(self._tr("filter_weekends"))
        self.chk_vacations.setText(self._tr("filter_vacations"))
        self.chk_school.setText(self._tr("filter_school"))

        self.export_excel_btn.setText(self._tr("btn_export_excel"))
        self.export_ical_btn.setText(self._tr("btn_export_ical"))
        self.add_vacation_btn.setText(self._tr("btn_add_vacation"))

        self.month_table.setHorizontalHeaderLabels(
            [self._tr("month_col_kw"), self._tr("month_col_weekday"),
             self._tr("month_col_date"), self._tr("month_col_description")]
        )
        self.list_table.setHorizontalHeaderLabels(
            [self._tr("list_col_date"), self._tr("list_col_weekday"), self._tr("list_col_type"),
             self._tr("list_col_country"), self._tr("list_col_description"), self._tr("list_col_kw")]
        )
        self.vacations_table.setHorizontalHeaderLabels(
            [self._tr("vac_col_name"), self._tr("vac_col_date_range"), self._tr("vac_col_working_days"), ""]
        )

        self.vacations_group_box.setTitle(self._tr("panel_planned_vacations"))
        self.budget_group_box.setTitle(self._tr("panel_vacation_budget"))
        self._label_base_days.setText(self._tr("budget_base_days"))
        self._label_overtime_hours.setText(self._tr("budget_overtime_hours"))
        self._label_hours_per_day.setText(self._tr("budget_hours_per_day"))

        self._render_vacations_panel()
        self._render_budget_panel()
        self._rebuild_current_view()

    def _go_to_today(self) -> None:
        today = date.today()
        self.selected_year = today.year
        self.selected_month = today.month
        self._year_follows_today = True
        self.year_combo.blockSignals(True)
        if today.year in YEARS:
            self.year_combo.setCurrentIndex(YEARS.index(today.year))
        self.year_combo.blockSignals(False)
        self._set_view_mode("month")
        self.refresh_data()

    def _set_view_mode(self, mode: str) -> None:
        self.view_mode = mode
        for name in ("year", "month", "list"):
            getattr(self, f"_view_btn_{name}").setChecked(name == mode)
        self.stack.setCurrentIndex({"year": 0, "month": 1, "list": 2}[mode])
        self._rebuild_current_view()

    def _prev_month(self) -> None:
        self.selected_month -= 1
        if self.selected_month < 1:
            self.selected_month = 12
        self._render_month_view()

    def _next_month(self) -> None:
        self.selected_month += 1
        if self.selected_month > 12:
            self.selected_month = 1
        self._render_month_view()

    def _on_filters_changed(self) -> None:
        self.show_holidays = self.chk_holidays.isChecked()
        self.show_bridge_days = self.chk_bridge.isChecked()
        self.show_weekends = self.chk_weekends.isChecked()
        self.show_vacations = self.chk_vacations.isChecked()
        self.show_school_holidays = self.chk_school.isChecked()
        self._rebuild_current_view()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Wait for any in-flight network fetch before the window closes.

        Without this, closing the app while a holiday fetch is still
        running destroys the QThread mid-flight, which Qt logs as
        "QThread: Destroyed while thread ... is still running" and can
        abort the process. Found via a headless test run during
        development (see project feedback log).
        """
        for thread in (self._fetch_thread, self._prefetch_thread):
            try:
                if thread is not None and thread.isRunning():
                    thread.quit()
                    thread.wait(3000)
            except RuntimeError:
                # Underlying C++ QThread was already destroyed (fetch finished
                # between the None-check above and isRunning()) - nothing to
                # wait for in that case.
                pass
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Vacations
    # ------------------------------------------------------------------
    def _add_vacation(self) -> None:
        dialog = VacationDialog(self._holiday_dates(self.selected_country), parent=self)
        if dialog.exec() and dialog.result_vacation:
            self.vacations.append(dialog.result_vacation)
            save_vacations(self.vacations)
            self._render_vacations_panel()
            self._render_budget_panel()
            self._rebuild_current_view()

    def _edit_vacation(self, vacation: Vacation) -> None:
        dialog = VacationDialog(
            self._holiday_dates(self.selected_country), vacation=vacation, parent=self
        )
        if dialog.exec() and dialog.result_vacation:
            self.vacations = [
                dialog.result_vacation if v.id == vacation.id else v for v in self.vacations
            ]
            save_vacations(self.vacations)
            self._render_vacations_panel()
            self._render_budget_panel()
            self._rebuild_current_view()

    def _remove_vacation(self, vacation: Vacation) -> None:
        confirm = QMessageBox.question(
            self,
            "Remove Vacation",
            f'Remove "{vacation.name}" ({vacation.start_date} - {vacation.end_date})?',
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.vacations = [v for v in self.vacations if v.id != vacation.id]
        save_vacations(self.vacations)
        self._render_vacations_panel()
        self._render_budget_panel()
        self._rebuild_current_view()

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def _export_excel(self) -> None:
        days = [d for d in self._generate_year(self.selected_year) if self._day_passes_filters(d)]
        default_name = self._export_filename("xlsx")
        path_str, _ = QFileDialog.getSaveFileName(self, "Export to Excel", default_name, "Excel (*.xlsx)")
        if not path_str:
            return
        try:
            export.export_to_excel(
                days, Path(path_str), self.selected_country, self.selected_country2, self.selected_year
            )
            self.statusBar().showMessage(f"Exported to {path_str}", 5000)
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

    def _export_ical(self) -> None:
        days = [d for d in self._generate_year(self.selected_year) if self._day_passes_filters(d)]
        default_name = self._export_filename("ics")
        path_str, _ = QFileDialog.getSaveFileName(self, "Export to iCal", default_name, "iCalendar (*.ics)")
        if not path_str:
            return
        country_name = COUNTRY_NAME_BY_CODE.get(self.selected_country, self.selected_country)
        try:
            export.export_to_ical(days, Path(path_str), country_name)
            self.statusBar().showMessage(f"Exported to {path_str}", 5000)
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

    def _export_filename(self, extension: str) -> str:
        if self.selected_country2:
            return f"Business_Finder_{self.selected_country}_vs_{self.selected_country2}_{self.selected_year}.{extension}"
        return f"Business_Finder_{self.selected_country}_{self.selected_year}.{extension}"
