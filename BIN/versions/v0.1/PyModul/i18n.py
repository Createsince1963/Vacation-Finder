"""Small, dict-based UI translation layer.

Deliberately NOT Qt Linguist (.ts/.qm files) - this app has a modest,
fixed set of UI labels, so a plain Python dict is simpler to maintain and
needs no extra build/compile step for the Android APK build. If the UI
text ever grows substantially, switching to Qt's translation system would
scale better than this.

Coverage: static UI chrome (toolbar labels, buttons, panel titles, table
headers) and the small set of dynamic descriptor words the calendar views
build up at render time (day types, "Ready", budget-line phrases, month
names). NOT covered (left in English, a reasonable v1 scope cut for a
"kleine" - small - config addition): native OS file-dialog chrome, error
message text, and weekday names (Python's ``date.strftime("%A")`` is
locale-dependent and would need the OS locale changed, not just this
dict, to translate).
"""

from __future__ import annotations

# (code, native display name shown in the language picker itself)
SUPPORTED_LANGUAGES: list[tuple[str, str]] = [
    ("en", "English"),
    ("de", "Deutsch"),
    ("es", "Español"),
    ("fr", "Français"),
    ("pt", "Português"),
    ("it", "Italiano"),
    ("zh", "中文"),
    ("ar", "العربية"),
]

DEFAULT_LANGUAGE = "en"
_LANGUAGE_CODES = [code for code, _ in SUPPORTED_LANGUAGES]

# One row per key: (key, en, de, es, fr, pt, it, zh, ar)
# Column order matches _LANGUAGE_CODES above.
_ROWS: list[tuple[str, ...]] = [
    ("toolbar_country", "Country", "Land", "País", "Pays", "País", "Paese", "国家", "الدولة"),
    ("toolbar_state", "State", "Bundesland", "Región", "Région", "Estado", "Regione", "州/省", "المنطقة"),
    ("toolbar_compare_with", "Compare with", "Vergleichen mit", "Comparar con", "Comparer avec", "Comparar com", "Confronta con", "对比", "مقارنة مع"),
    ("toolbar_year", "Year", "Jahr", "Año", "Année", "Ano", "Anno", "年份", "السنة"),
    ("toolbar_max_bridge_gap", "Max bridge gap", "Max. Brückentag-Lücke", "Puente máx.", "Pont max.", "Ponte máx.", "Ponte max.", "最大桥接天数", "أقصى فجوة جسر"),
    ("toolbar_search_placeholder", "Search holidays...", "Feiertage suchen...", "Buscar festivos...", "Rechercher des jours fériés...", "Pesquisar feriados...", "Cerca festività...", "搜索假期...", "البحث عن العطلات..."),
    ("toolbar_today", "Today", "Heute", "Hoy", "Aujourd'hui", "Hoje", "Oggi", "今天", "اليوم"),
    ("toolbar_language", "Language", "Sprache", "Idioma", "Langue", "Idioma", "Lingua", "语言", "اللغة"),
    ("view_year", "Year", "Jahr", "Año", "Année", "Ano", "Anno", "年", "سنة"),
    ("view_month", "Month", "Monat", "Mes", "Mois", "Mês", "Mese", "月", "شهر"),
    ("view_list", "List", "Liste", "Lista", "Liste", "Lista", "Elenco", "列表", "قائمة"),
    ("filter_holidays", "Holidays", "Feiertage", "Festivos", "Jours fériés", "Feriados", "Festività", "假日", "العطلات"),
    ("filter_bridge_days", "Bridge Days", "Brückentage", "Días puente", "Ponts", "Dias de ponte", "Ponti", "桥接日", "أيام الجسر"),
    ("filter_weekends", "Weekends", "Wochenenden", "Fines de semana", "Week-ends", "Fins de semana", "Fine settimana", "周末", "عطلات نهاية الأسبوع"),
    ("filter_vacations", "Vacations", "Urlaub", "Vacaciones", "Congés", "Férias", "Ferie", "休假", "الإجازات"),
    ("filter_school", "School", "Schule", "Escuela", "École", "Escola", "Scuola", "学校", "المدرسة"),
    ("btn_export_excel", "Export Excel", "Excel exportieren", "Exportar a Excel", "Exporter en Excel", "Exportar para Excel", "Esporta in Excel", "导出为 Excel", "تصدير إلى Excel"),
    ("btn_export_ical", "Export iCal", "iCal exportieren", "Exportar a iCal", "Exporter en iCal", "Exportar para iCal", "Esporta in iCal", "导出为 iCal", "تصدير إلى iCal"),
    ("btn_add_vacation", "Add Vacation", "Urlaub hinzufügen", "Añadir vacaciones", "Ajouter un congé", "Adicionar férias", "Aggiungi ferie", "添加休假", "إضافة إجازة"),
    ("btn_edit", "Edit", "Bearbeiten", "Editar", "Modifier", "Editar", "Modifica", "编辑", "تعديل"),
    ("btn_remove", "Remove", "Entfernen", "Eliminar", "Supprimer", "Remover", "Rimuovi", "删除", "إزالة"),
    ("panel_vacation_budget", "Vacation Budget", "Urlaubskonto", "Saldo de vacaciones", "Solde de congés", "Saldo de férias", "Saldo ferie", "假期余额", "رصيد الإجازات"),
    ("panel_planned_vacations", "Planned Vacations", "Geplanter Urlaub", "Vacaciones planificadas", "Congés planifiés", "Férias planeadas", "Ferie pianificate", "已计划休假", "الإجازات المخطط لها"),
    ("budget_base_days", "Base days/year", "Basistage/Jahr", "Días base/año", "Jours de base/an", "Dias base/ano", "Giorni base/anno", "基础天数/年", "الأيام الأساسية/سنة"),
    ("budget_overtime_hours", "Overtime hours", "Überstunden", "Horas extra", "Heures supplémentaires", "Horas extra", "Ore di straordinario", "加班小时数", "ساعات العمل الإضافي"),
    ("budget_hours_per_day", "Hours/day", "Stunden/Tag", "Horas/día", "Heures/jour", "Horas/dia", "Ore/giorno", "小时/天", "ساعات/يوم"),
    ("month_col_kw", "KW", "KW", "Sem.", "Sem.", "Sem.", "Sett.", "周", "أسبوع"),
    ("month_col_weekday", "Weekday", "Wochentag", "Día", "Jour", "Dia", "Giorno", "星期", "اليوم"),
    ("month_col_date", "Date", "Datum", "Fecha", "Date", "Data", "Data", "日期", "التاريخ"),
    ("month_col_description", "Description", "Beschreibung", "Descripción", "Description", "Descrição", "Descrizione", "说明", "الوصف"),
    ("list_col_date", "Date", "Datum", "Fecha", "Date", "Data", "Data", "日期", "التاريخ"),
    ("list_col_weekday", "Weekday", "Wochentag", "Día", "Jour", "Dia", "Giorno", "星期", "اليوم"),
    ("list_col_type", "Type", "Typ", "Tipo", "Type", "Tipo", "Tipo", "类型", "النوع"),
    ("list_col_country", "Country", "Land", "País", "Pays", "País", "Paese", "国家", "الدولة"),
    ("list_col_description", "Description", "Beschreibung", "Descripción", "Description", "Descrição", "Descrizione", "说明", "الوصف"),
    ("list_col_kw", "KW", "KW", "Sem.", "Sem.", "Sem.", "Sett.", "周", "أسبوع"),
    ("vac_col_name", "Name", "Name", "Nombre", "Nom", "Nome", "Nome", "名称", "الاسم"),
    ("vac_col_date_range", "Date Range", "Zeitraum", "Periodo", "Période", "Período", "Periodo", "日期范围", "الفترة"),
    ("vac_col_working_days", "Working Days", "Arbeitstage", "Días laborables", "Jours ouvrés", "Dias úteis", "Giorni lavorativi", "工作日", "أيام العمل"),
    ("day_type_holiday", "Holiday", "Feiertag", "Festivo", "Jour férié", "Feriado", "Festività", "假日", "عطلة"),
    ("day_type_vacation", "Vacation", "Urlaub", "Vacaciones", "Congé", "Férias", "Ferie", "休假", "إجازة"),
    ("day_type_bridge_day", "Bridge Day", "Brückentag", "Día puente", "Pont", "Dia de ponte", "Ponte", "桥接日", "يوم جسر"),
    ("day_type_school_holiday", "School Holiday", "Schulferien", "Vacaciones escolares", "Vacances scolaires", "Férias escolares", "Vacanze scolastiche", "学校假期", "عطلة مدرسية"),
    ("day_type_weekend", "Weekend", "Wochenende", "Fin de semana", "Week-end", "Fim de semana", "Fine settimana", "周末", "عطلة نهاية الأسبوع"),
    ("desc_standard_business_day", "Standard Business Day", "Regulärer Arbeitstag", "Día laborable normal", "Jour ouvré normal", "Dia útil normal", "Giorno lavorativo normale", "正常工作日", "يوم عمل عادي"),
    ("desc_personal_vacation", "Personal Vacation", "Persönlicher Urlaub", "Vacaciones personales", "Congé personnel", "Férias pessoais", "Ferie personali", "个人休假", "إجازة شخصية"),
    ("desc_strategic_bridge_day", "Strategic Bridge Day", "Strategischer Brückentag", "Día puente estratégico", "Pont stratégique", "Ponte estratégica", "Ponte strategico", "战略桥接日", "يوم جسر استراتيجي"),
    ("status_ready", "Ready", "Bereit", "Listo", "Prêt", "Pronto", "Pronto", "就绪", "جاهز"),
    ("vac_total_planned", "Total planned", "Gesamt geplant", "Total planificado", "Total planifié", "Total planeado", "Totale pianificato", "计划总计", "الإجمالي المخطط له"),
    ("label_working_days_unit", "working day(s)", "Arbeitstag(e)", "día(s) laborable(s)", "jour(s) ouvré(s)", "dia(s) útil(eis)", "giorno/i lavorativo/i", "个工作日", "يوم عمل"),
    ("label_days_unit", "day(s)", "Tag(e)", "día(s)", "jour(s)", "dia(s)", "giorno/i", "天", "يوم"),
    ("budget_available", "available", "verfügbar", "disponible", "disponible", "disponível", "disponibile", "可用", "متاح"),
    ("budget_base_word", "base", "Basis", "base", "base", "base", "base", "基础", "أساسي"),
    ("budget_from_overtime", "from overtime", "aus Überstunden", "de horas extra", "d'heures sup.", "de horas extra", "da straordinari", "来自加班", "من العمل الإضافي"),
    ("budget_carried_over", "carried over", "übertragen", "trasladado", "reporté", "transitado", "riportato", "结转", "مرحّل"),
    ("budget_used", "Used", "Verbraucht", "Usado", "Utilisé", "Usado", "Utilizzato", "已用", "مستخدم"),
    ("budget_remaining", "Remaining", "Verbleibend", "Restante", "Restant", "Restante", "Rimanente", "剩余", "متبقٍ"),
    ("list_days_found", "total days found", "Tage insgesamt gefunden", "días encontrados en total", "jours trouvés au total", "dias encontrados no total", "giorni trovati in totale", "共找到天数", "إجمالي الأيام الموجودة"),
    ("month_01", "January", "Januar", "enero", "janvier", "janeiro", "gennaio", "一月", "يناير"),
    ("month_02", "February", "Februar", "febrero", "février", "fevereiro", "febbraio", "二月", "فبراير"),
    ("month_03", "March", "März", "marzo", "mars", "março", "marzo", "三月", "مارس"),
    ("month_04", "April", "April", "abril", "avril", "abril", "aprile", "四月", "أبريل"),
    ("month_05", "May", "Mai", "mayo", "mai", "maio", "maggio", "五月", "مايو"),
    ("month_06", "June", "Juni", "junio", "juin", "junho", "giugno", "六月", "يونيو"),
    ("month_07", "July", "Juli", "julio", "juillet", "julho", "luglio", "七月", "يوليو"),
    ("month_08", "August", "August", "agosto", "août", "agosto", "agosto", "八月", "أغسطس"),
    ("month_09", "September", "September", "septiembre", "septembre", "setembro", "settembre", "九月", "سبتمبر"),
    ("month_10", "October", "Oktober", "octubre", "octobre", "outubro", "ottobre", "十月", "أكتوبر"),
    ("month_11", "November", "November", "noviembre", "novembre", "novembro", "novembre", "十一月", "نوفمبر"),
    ("month_12", "December", "Dezember", "diciembre", "décembre", "dezembro", "dicembre", "十二月", "ديسمبر"),
]

# Build {lang_code: {key: text}} from the table above.
_TRANSLATIONS: dict[str, dict[str, str]] = {code: {} for code in _LANGUAGE_CODES}
for _row in _ROWS:
    _key, *_texts = _row
    for _code, _text in zip(_LANGUAGE_CODES, _texts):
        _TRANSLATIONS[_code][_key] = _text

MONTH_KEYS = [f"month_{i:02d}" for i in range(1, 13)]


def tr(key: str, lang: str) -> str:
    """Translate `key` into `lang`. Falls back to English, then to the raw
    key itself, so a missing/mistyped key never crashes the UI - it just
    shows up untranslated (visible during development, harmless in use)."""
    table = _TRANSLATIONS.get(lang) or _TRANSLATIONS[DEFAULT_LANGUAGE]
    return table.get(key) or _TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)


def month_names(lang: str) -> list[str]:
    """Full month names (January..December) in the given language."""
    return [tr(k, lang) for k in MONTH_KEYS]
