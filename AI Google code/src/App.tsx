import React, { useState, useEffect, useMemo, useRef } from 'react';
import { 
  Calendar as CalendarIcon, 
  Globe, 
  Search, 
  ChevronDown, 
  Info, 
  AlertCircle, 
  Loader2, 
  Filter,
  RefreshCw,
  ArrowRight,
  Briefcase,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  MessageSquare,
  Send,
  X,
  Maximize2,
  Minimize2,
  CalendarDays,
  Target,
  Download,
  FileText,
  List as ListIcon,
  HelpCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { GoogleGenAI } from "@google/genai";
import Markdown from 'react-markdown';
import * as XLSX from 'xlsx';
import { createEvents, EventAttributes } from 'ics';
import { COUNTRIES, YEARS } from './constants';
import { Holiday, OpenHoliday, CalendarDay, Vacation, Subdivision, SchoolHoliday } from './types';

type ApiSource = 'nager' | 'openholidays';
type ViewMode = 'year' | 'month' | 'list';

// Initialize Gemini
const genAI = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY || '' });

export default function App() {
  // State
  const [selectedCountry, setSelectedCountry] = useState('DE');
  const [selectedSubdivision, setSelectedSubdivision] = useState<string | null>(null);
  const [subdivisions, setSubdivisions] = useState<Subdivision[]>([]);
  const [selectedCountry2, setSelectedCountry2] = useState<string | null>(null);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth());
  const [viewMode, setViewMode] = useState<ViewMode>('year');
  const [apiSource, setApiSource] = useState<ApiSource>('nager');
  const [holidays, setHolidays] = useState<Holiday[]>([]);
  const [schoolHolidays, setSchoolHolidays] = useState<SchoolHoliday[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  
  const [vacations, setVacations] = useState<Vacation[]>(() => {
    const saved = typeof window !== 'undefined' ? localStorage.getItem('business_finder_vacations') : null;
    return saved ? JSON.parse(saved) : [];
  });

  const totalVacationDays = useMemo(() => {
    return vacations.reduce((sum, v) => {
      let count = 0;
      const start = new Date(v.startDate);
      const end = new Date(v.endDate);
      const current = new Date(start);

      while (current <= end) {
        const dateStr = formatDate(current);
        const isWeekend = current.getDay() === 0 || current.getDay() === 6;
        const isHoliday = holidays.some(h => h.date === dateStr);
        
        if (!isWeekend && !isHoliday) {
          count++;
        }
        current.setDate(current.getDate() + 1);
      }
      return sum + count;
    }, 0);
  }, [vacations, holidays]);

  useEffect(() => {
    localStorage.setItem('business_finder_vacations', JSON.stringify(vacations));
  }, [vacations]);

  const [editingVacation, setEditingVacation] = useState<Vacation | null>(null);

  const addVacation = (v: Omit<Vacation, 'id'>) => {
    setVacations(prev => [...prev, { ...v, id: Math.random().toString(36).substr(2, 9) }]);
  };

  const updateVacation = (v: Vacation) => {
    setVacations(prev => prev.map(item => item.id === v.id ? v : item));
  };

  const removeVacation = (id: string) => {
    setVacations(prev => prev.filter(v => v.id !== id));
  };

  const [showVacationModal, setShowVacationModal] = useState(false);
  const [vacationForm, setVacationForm] = useState({
    startDate: '',
    endDate: ''
  });

  useEffect(() => {
    if (editingVacation) {
      setVacationForm({
        startDate: editingVacation.startDate,
        endDate: editingVacation.endDate
      });
    } else {
      setVacationForm({
        startDate: '',
        endDate: ''
      });
    }
  }, [editingVacation, showVacationModal]);

  const calculateWorkingDays = (startStr: string, endStr: string) => {
    if (!startStr || !endStr) return 0;
    let count = 0;
    const start = new Date(startStr);
    const end = new Date(endStr);
    const current = new Date(start);
    while (current <= end) {
      const dateStr = formatDate(current);
      const isWeekend = current.getDay() === 0 || current.getDay() === 6;
      const isHoliday = holidays.some(h => h.date === dateStr);
      if (!isWeekend && !isHoliday) count++;
      current.setDate(current.getDate() + 1);
    }
    return count;
  };

  // Toggles
  const [showHolidays, setShowHolidays] = useState(true);
  const [showSchoolHolidays, setShowSchoolHolidays] = useState(false);
  const [showBridgeDays, setShowBridgeDays] = useState(true);
  const [showWeekends, setShowWeekends] = useState(true);
  const [showVacations, setShowVacations] = useState(true);
  const [comparisonFilter, setComparisonFilter] = useState<'all' | 'common' | 'unique'>('all');
  
  // Chatbot State
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState<{ role: 'user' | 'model', text: string }[]>([
    { role: 'model', text: 'Hello! I am your Thomas Vacation Finder assistant. Ask me anything about global holidays or bridge day planning.' }
  ]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Helper: Format Date to YYYY-MM-DD (Local)
  const formatDate = (date: Date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  // Helper: Get Week Number
  const getWeekNumber = (d: Date) => {
    const date = new Date(d.getTime());
    date.setHours(0, 0, 0, 0);
    date.setDate(date.getDate() + 3 - (date.getDay() + 6) % 7);
    const week1 = new Date(date.getFullYear(), 0, 4);
    return 1 + Math.round(((date.getTime() - week1.getTime()) / 86400000 - 3 + (week1.getDay() + 6) % 7) / 7);
  };

  // Helper: Check Bridge Day
  const isBridgeDay = (date: Date, holidayDates: Set<string>) => {
    const day = date.getDay();
    const dateStr = formatDate(date);
    if (holidayDates.has(dateStr)) return false;

    // Bridge Day Logic (Up to 2 days):
    const checkOffset = (offset: number) => {
      const d = new Date(date);
      d.setDate(date.getDate() + offset);
      return holidayDates.has(formatDate(d));
    };

    // Mon: Bridge if Tue is holiday (1d) OR Wed is holiday (2d)
    if (day === 1) return checkOffset(1) || checkOffset(2);
    // Tue: Bridge if Mon is holiday (1d) OR Wed is holiday (1d)
    if (day === 2) return checkOffset(-1) || checkOffset(1);
    // Wed: Bridge if Tue is holiday (1d) OR Thu is holiday (1d)
    if (day === 3) return checkOffset(-1) || checkOffset(1);
    // Thu: Bridge if Wed is holiday (1d) OR Fri is holiday (1d)
    if (day === 4) return checkOffset(-1) || checkOffset(1);
    // Fri: Bridge if Thu is holiday (1d) OR Wed is holiday (2d)
    if (day === 5) return checkOffset(-1) || checkOffset(-2);
    
    return false;
  };

  // Fetch Subdivisions
  const fetchSubdivisions = async (countryCode: string) => {
    try {
      const res = await fetch(`https://openholidaysapi.org/Subdivisions?countryIsoCode=${countryCode}`);
      if (!res.ok) return [];
      return await res.json();
    } catch (err) {
      console.error(err);
      return [];
    }
  };

  // Fetch School Holidays
  const fetchSchoolHolidays = async (countryCode: string, subdivisionCode?: string | null) => {
    try {
      let url = `https://openholidaysapi.org/SchoolHolidays?countryIsoCode=${countryCode}&languageIsoCode=EN&validFrom=${selectedYear}-01-01&validTo=${selectedYear}-12-31`;
      if (subdivisionCode) {
        url += `&subdivisionCode=${subdivisionCode}`;
      }
      const res = await fetch(url);
      if (!res.ok) return [];
      const raw: SchoolHoliday[] = await res.json();
      return raw;
    } catch (err) {
      console.error(err);
      return [];
    }
  };

  // Fetch Holidays for a specific country
  const fetchCountryHolidays = async (countryCode: string) => {
    try {
      let data: Holiday[] = [];
      if (apiSource === 'nager') {
        const res = await fetch(`https://date.nager.at/api/v3/PublicHolidays/${selectedYear}/${countryCode}`);
        if (!res.ok) throw new Error(`Nager.Date API error for ${countryCode}`);
        data = await res.json();
      } else {
        const res = await fetch(`https://openholidaysapi.org/PublicHolidays?countryIsoCode=${countryCode}&languageIsoCode=EN&validFrom=${selectedYear}-01-01&validTo=${selectedYear}-12-31`);
        if (!res.ok) throw new Error(`OpenHolidays API error for ${countryCode}`);
        const raw: OpenHoliday[] = await res.json();
        data = raw.map(oh => ({
          date: oh.startDate,
          localName: oh.name[0].text,
          name: oh.name.find(n => n.language === 'EN')?.text || oh.name[0].text,
          countryCode: countryCode,
          fixed: true,
          global: oh.nationwide,
          counties: null,
          launchYear: null,
          types: [oh.type]
        }));
      }
      return data;
    } catch (err) {
      console.error(err);
      return [];
    }
  };

  // Fetch Holidays
  const fetchHolidays = async () => {
    setLoading(true);
    setError(null);
    try {
      const h1 = await fetchCountryHolidays(selectedCountry);
      let h2: Holiday[] = [];
      if (selectedCountry2) {
        h2 = await fetchCountryHolidays(selectedCountry2);
      }
      setHolidays([...h1, ...h2]);

      // Fetch School Holidays
      const sh = await fetchSchoolHolidays(selectedCountry, selectedSubdivision);
      setSchoolHolidays(sh);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const loadSubdivisions = async () => {
      const subs = await fetchSubdivisions(selectedCountry);
      setSubdivisions(subs);
      setSelectedSubdivision(null); // Reset subdivision when country changes
    };
    loadSubdivisions();
  }, [selectedCountry]);

  useEffect(() => {
    fetchHolidays();
  }, [selectedCountry, selectedSubdivision, selectedCountry2, selectedYear, apiSource]);

  // Calendar Generation
  const holidayDates1 = useMemo(() => new Set(holidays.filter(h => h.countryCode === selectedCountry).map(h => h.date)), [holidays, selectedCountry]);
  const holidayDates2 = useMemo(() => new Set(holidays.filter(h => h.countryCode === selectedCountry2).map(h => h.date)), [holidays, selectedCountry2]);
  const holidayDatesAll = useMemo(() => new Set(holidays.map(h => h.date)), [holidays]);

  const generateMonthDays = (year: number, month: number) => {
    const days: CalendarDay[] = [];
    const lastDay = new Date(year, month + 1, 0);
    
    for (let d = 1; d <= lastDay.getDate(); d++) {
      const date = new Date(year, month, d);
      const dateStr = formatDate(date);
      const dayHolidays = holidays.filter(h => h.date === dateStr);
      
      const isBridge1 = isBridgeDay(date, holidayDates1);
      const isBridge2 = selectedCountry2 ? isBridgeDay(date, holidayDates2) : false;
      const bridgeDayCountries = [];
      if (isBridge1) bridgeDayCountries.push(selectedCountry);
      if (isBridge2 && selectedCountry2) bridgeDayCountries.push(selectedCountry2);

      // Vacation check
      const vacation = vacations.find(v => {
        const current = dateStr;
        return current >= v.startDate && current <= v.endDate;
      });

      // School Holiday check
      const schoolHoliday = schoolHolidays.find(sh => {
        const current = dateStr;
        return current >= sh.startDate && current <= sh.endDate;
      });

      days.push({
        date,
        isHoliday: dayHolidays.length > 0,
        holidayName: dayHolidays.map(h => h.name).join(', '),
        holidays: dayHolidays,
        isBridgeDay: bridgeDayCountries.length > 0,
        bridgeDayCountries,
        isWeekend: date.getDay() === 0 || date.getDay() === 6,
        weekNumber: getWeekNumber(date),
        isVacation: !!vacation,
        vacationName: vacation?.name,
        isSchoolHoliday: !!schoolHoliday,
        schoolHolidayName: schoolHoliday?.name[0].text
      });
    }
    return days;
  };

  // Chat Logic
  const handleSendMessage = async () => {
    if (!chatInput.trim()) return;
    const userMsg = chatInput;
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setIsChatLoading(true);

    try {
      const result = await genAI.models.generateContent({
        model: "gemini-3.1-pro-preview",
        contents: [{ role: 'user', parts: [{ text: userMsg }] }],
        config: { 
          systemInstruction: `You are a professional business consultant specializing in global holiday planning. 
          Current context: Primary Country ${selectedCountry}${selectedCountry2 ? `, Comparison Country ${selectedCountry2}` : ''}, Year ${selectedYear}. 
          Help users plan bridge days (now supporting up to 2-day spans) and understand international holiday impacts on business.
          When comparing countries, highlight overlaps and differences in non-working days.
          Always provide clear, actionable advice. Use markdown for lists and emphasis.`,
          tools: [{ googleSearch: {} }] 
        }
      });
      
      setChatMessages(prev => [...prev, { role: 'model', text: result.text || 'I am sorry, I could not generate a response.' }]);
    } catch (err) {
      setChatMessages(prev => [...prev, { role: 'model', text: 'Error connecting to Gemini. Please check your API key.' }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const countryName = COUNTRIES.find(c => c.code === selectedCountry)?.name || selectedCountry;
  const countryName2 = selectedCountry2 ? (COUNTRIES.find(c => c.code === selectedCountry2)?.name || selectedCountry2) : null;

  const goToToday = () => {
    const today = new Date();
    setSelectedYear(today.getFullYear());
    setSelectedMonth(today.getMonth());
    setViewMode('month');
  };

  const filteredHolidays = useMemo(() => {
    if (!searchTerm) return holidays;
    return holidays.filter(h => 
      h.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
      h.localName.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [holidays, searchTerm]);

  // Generate all relevant days for the year (for list view and export)
  const yearlyData = useMemo(() => {
    const allDays: CalendarDay[] = [];
    for (let m = 0; m < 12; m++) {
      allDays.push(...generateMonthDays(selectedYear, m));
    }
    
    return allDays.filter(day => {
      if (day.isHoliday && showHolidays) {
        if (selectedCountry2) {
          const codes = day.holidays?.map(h => h.countryCode) || [];
          const isCommon = codes.includes(selectedCountry) && codes.includes(selectedCountry2);
          if (comparisonFilter === 'common' && !isCommon) return false;
          if (comparisonFilter === 'unique' && isCommon) return false;
        }
        return true;
      }
      if (day.isBridgeDay && showBridgeDays) return true;
      if (day.isVacation && showVacations) return true;
      if (day.isSchoolHoliday && showSchoolHolidays) return true;
      if (day.isWeekend && showWeekends) return true;
      return false;
    }).sort((a, b) => a.date.getTime() - b.date.getTime());
  }, [selectedYear, holidays, vacations, schoolHolidays, showHolidays, showBridgeDays, showWeekends, showVacations, showSchoolHolidays, comparisonFilter, selectedCountry, selectedCountry2]);

  // Export to Excel
  const exportToExcel = () => {
    const data = yearlyData.map(day => ({
      Date: day.date.toLocaleDateString(),
      Weekday: day.date.toLocaleString('default', { weekday: 'long' }),
      Type: day.isHoliday ? 'Holiday' : day.isBridgeDay ? 'Bridge Day' : 'Weekend',
      Country: day.isHoliday 
        ? (day.holidays?.map(h => h.countryCode).join(', ') || '-')
        : (day.isBridgeDay ? (day.bridgeDayCountries?.join(', ') || '-') : '-'),
      Name: day.holidayName || (day.isBridgeDay ? 'Bridge Day' : 'Weekend'),
      KW: day.weekNumber
    }));

    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Holidays");
    const filename = selectedCountry2 ? 
      `Business_Finder_${selectedCountry}_vs_${selectedCountry2}_${selectedYear}.xlsx` : 
      `Business_Finder_${selectedCountry}_${selectedYear}.xlsx`;
    XLSX.writeFile(wb, filename);
  };

  // Export to iCal
  const exportToICal = () => {
    const events: EventAttributes[] = yearlyData.map(day => {
      const date = day.date;
      const countriesStr = day.isHoliday 
        ? (day.holidays?.map(h => h.countryCode).join(', ') || countryName)
        : (day.isBridgeDay ? (day.bridgeDayCountries?.join(', ') || countryName) : countryName);
      return {
        start: [date.getFullYear(), date.getMonth() + 1, date.getDate()],
        duration: { days: 1 },
        title: day.holidayName || (day.isBridgeDay ? 'Bridge Day' : 'Weekend'),
        description: `${day.isHoliday ? 'Public Holiday' : day.isBridgeDay ? 'Strategic Bridge Day' : 'Weekend'} in ${countriesStr}`,
        categories: [day.isHoliday ? 'Holiday' : day.isBridgeDay ? 'BridgeDay' : 'Weekend'],
        status: 'CONFIRMED',
        busyStatus: 'FREE'
      };
    });

    createEvents(events, (error, value) => {
      if (error) {
        console.error(error);
        return;
      }
      const blob = new Blob([value], { type: 'text/calendar;charset=utf-8' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const filename = selectedCountry2 ? 
        `Business_Finder_${selectedCountry}_vs_${selectedCountry2}_${selectedYear}.ics` : 
        `Business_Finder_${selectedCountry}_${selectedYear}.ics`;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    });
  };

  return (
    <div className="min-h-screen bg-[#F5F5F7] text-[#1D1D1F] font-sans selection:bg-blue-100 antialiased">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 bg-white/70 backdrop-blur-2xl border-b border-[#D2D2D7]/30">
        <div className="max-w-[1400px] mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-[#0071E3] rounded-lg flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Briefcase className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl tracking-tight">Thomas Vacation Finder (for Exyte......)</span>
          </div>
          
          <div className="flex items-center gap-6">
            <div className="hidden md:flex items-center gap-1 p-1 bg-[#F5F5F7]/50 rounded-xl border border-[#D2D2D7]/20">
              <button 
                onClick={() => setViewMode('year')}
                className={`px-4 py-1.5 text-xs font-semibold rounded-lg transition-all ${viewMode === 'year' ? 'bg-white shadow-sm text-[#0071E3]' : 'text-[#86868B] hover:text-[#1D1D1F]'}`}
              >
                Year
              </button>
              <button 
                onClick={() => setViewMode('month')}
                className={`px-4 py-1.5 text-xs font-semibold rounded-lg transition-all ${viewMode === 'month' ? 'bg-white shadow-sm text-[#0071E3]' : 'text-[#86868B] hover:text-[#1D1D1F]'}`}
              >
                Month
              </button>
              <button 
                onClick={() => setViewMode('list')}
                className={`px-4 py-1.5 text-xs font-semibold rounded-lg transition-all ${viewMode === 'list' ? 'bg-white shadow-sm text-[#0071E3]' : 'text-[#86868B] hover:text-[#1D1D1F]'}`}
              >
                List
              </button>
            </div>
            
            <div className="h-6 w-px bg-[#D2D2D7]/50 hidden md:block" />

            <button 
              onClick={() => setShowHelp(true)}
              className="p-2 hover:bg-[#F5F5F7] rounded-full transition-all text-[#86868B] hover:text-[#1D1D1F]"
              title="Help & Documentation"
            >
              <HelpCircle className="w-5 h-5" />
            </button>

            <button 
              onClick={() => setIsChatOpen(true)}
              className="group relative p-2.5 hover:bg-[#F5F5F7] rounded-full transition-all text-[#0071E3]"
            >
              <MessageSquare className="w-5 h-5" />
              <span className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full border-2 border-white" />
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-[1400px] mx-auto px-6 py-10">
        {/* Header Section */}
        <div className="mb-12 flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <h1 className="text-5xl font-bold tracking-tight mb-3">
              {countryName}
              <span className="text-[#86868B] ml-4">{selectedYear}</span>
            </h1>
            <p className="text-[#86868B] text-lg font-medium">Global non-working days and business optimization.</p>
            <div className="mt-2 flex items-center gap-2 text-xs font-bold text-[#0071E3] uppercase tracking-widest bg-blue-50 w-fit px-3 py-1 rounded-full border border-blue-100">
              <Globe className="w-3 h-3" />
              {COUNTRIES.length} Länder, hunderte Bundesländer & tausende Feiertage integriert
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <button 
              onClick={goToToday}
              className="flex items-center gap-2 px-5 py-2.5 bg-white border border-[#D2D2D7] rounded-full text-sm font-semibold hover:bg-[#F5F5F7] transition-all shadow-sm active:scale-95"
            >
              <Target className="w-4 h-4" />
              Today
            </button>
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-[#86868B]" />
              <input 
                type="text" 
                placeholder="Search holidays..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="pl-11 pr-6 py-2.5 bg-white border border-[#D2D2D7] rounded-full text-sm font-medium focus:ring-4 focus:ring-blue-500/10 outline-none transition-all w-64 shadow-sm"
              />
            </div>
          </div>
        </div>

        {/* Controls Bar */}
        <div className="flex flex-wrap items-center justify-between gap-8 mb-12 bg-white/80 backdrop-blur-md p-8 rounded-[32px] border border-white shadow-xl shadow-black/5">
          <div className="flex flex-wrap items-center gap-10">
            <div className="space-y-2">
              <label className="text-[11px] font-bold text-[#86868B] uppercase tracking-[0.15em]">Primary Region</label>
              <div className="flex items-center gap-4">
                <div className="relative group">
                  <select 
                    value={selectedCountry} 
                    onChange={(e) => setSelectedCountry(e.target.value)}
                    className="bg-transparent font-bold text-xl outline-none appearance-none pr-8 cursor-pointer text-[#1D1D1F] hover:text-[#0071E3] transition-colors"
                  >
                    {COUNTRIES.map(c => <option key={c.code} value={c.code}>{c.name}</option>)}
                  </select>
                  <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 w-5 h-5 text-[#86868B] pointer-events-none group-hover:text-[#0071E3] transition-colors" />
                </div>

                {subdivisions.length > 0 && (
                  <div className="relative group border-l border-[#D2D2D7]/50 pl-4">
                    <select 
                      value={selectedSubdivision || ''} 
                      onChange={(e) => setSelectedSubdivision(e.target.value || null)}
                      className="bg-transparent font-bold text-xl outline-none appearance-none pr-8 cursor-pointer text-[#1D1D1F] hover:text-[#0071E3] transition-colors"
                    >
                      <option value="">All States</option>
                      {subdivisions.map(s => <option key={s.code} value={s.code}>{s.name[0].text}</option>)}
                    </select>
                    <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 w-5 h-5 text-[#86868B] pointer-events-none group-hover:text-[#0071E3] transition-colors" />
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-[11px] font-bold text-[#86868B] uppercase tracking-[0.15em]">Compare with (Optional)</label>
              <div className="relative group">
                <select 
                  value={selectedCountry2 || ''} 
                  onChange={(e) => setSelectedCountry2(e.target.value || null)}
                  className="bg-transparent font-bold text-xl outline-none appearance-none pr-8 cursor-pointer text-[#1D1D1F] hover:text-[#0071E3] transition-colors"
                >
                  <option value="">None</option>
                  {COUNTRIES.filter(c => c.code !== selectedCountry).map(c => <option key={c.code} value={c.code}>{c.name}</option>)}
                </select>
                <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 w-5 h-5 text-[#86868B] pointer-events-none group-hover:text-[#0071E3] transition-colors" />
              </div>
            </div>

            <div className="w-px h-10 bg-[#D2D2D7]/50 hidden lg:block" />

            <div className="space-y-2">
              <label className="text-[11px] font-bold text-[#86868B] uppercase tracking-[0.15em]">Timeline</label>
              <div className="relative group">
                <select 
                  value={selectedYear} 
                  onChange={(e) => setSelectedYear(Number(e.target.value))}
                  className="bg-transparent font-bold text-xl outline-none appearance-none pr-8 cursor-pointer text-[#1D1D1F] hover:text-[#0071E3] transition-colors"
                >
                  {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
                </select>
                <ChevronDown className="absolute right-0 top-1/2 -translate-y-1/2 w-5 h-5 text-[#86868B] pointer-events-none group-hover:text-[#0071E3] transition-colors" />
              </div>
            </div>

            <div className="w-px h-10 bg-[#D2D2D7]/50 hidden lg:block" />

            <div className="flex flex-wrap items-center gap-8">
              <label className="flex items-center gap-3 cursor-pointer group">
                <input type="checkbox" checked={showHolidays} onChange={e => setShowHolidays(e.target.checked)} className="sr-only peer" />
                <div className="w-10 h-5 bg-[#D2D2D7] rounded-full peer-checked:bg-[#0071E3] relative transition-all duration-300">
                  <div className="absolute left-1 top-1 w-3 h-3 bg-white rounded-full transition-transform duration-300 peer-checked:translate-x-5" />
                </div>
                <span className="text-sm font-semibold text-[#86868B] group-hover:text-[#1D1D1F] transition-colors">Holidays</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer group">
                <input type="checkbox" checked={showBridgeDays} onChange={e => setShowBridgeDays(e.target.checked)} className="sr-only peer" />
                <div className="w-10 h-5 bg-[#D2D2D7] rounded-full peer-checked:bg-[#34C759] relative transition-all duration-300">
                  <div className="absolute left-1 top-1 w-3 h-3 bg-white rounded-full transition-transform duration-300 peer-checked:translate-x-5" />
                </div>
                <span className="text-sm font-semibold text-[#86868B] group-hover:text-[#1D1D1F] transition-colors">Bridge Days</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer group">
                <input type="checkbox" checked={showWeekends} onChange={e => setShowWeekends(e.target.checked)} className="sr-only peer" />
                <div className="w-10 h-5 bg-[#D2D2D7] rounded-full peer-checked:bg-orange-400 relative transition-all duration-300">
                  <div className="absolute left-1 top-1 w-3 h-3 bg-white rounded-full transition-transform duration-300 peer-checked:translate-x-5" />
                </div>
                <span className="text-sm font-semibold text-[#86868B] group-hover:text-[#1D1D1F] transition-colors">Weekends</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer group">
                <input type="checkbox" checked={showVacations} onChange={e => setShowVacations(e.target.checked)} className="sr-only peer" />
                <div className="w-10 h-5 bg-[#D2D2D7] rounded-full peer-checked:bg-purple-500 relative transition-all duration-300">
                  <div className="absolute left-1 top-1 w-3 h-3 bg-white rounded-full transition-transform duration-300 peer-checked:translate-x-5" />
                </div>
                <span className="text-sm font-semibold text-[#86868B] group-hover:text-[#1D1D1F] transition-colors">Vacations</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer group">
                <input type="checkbox" checked={showSchoolHolidays} onChange={e => setShowSchoolHolidays(e.target.checked)} className="sr-only peer" />
                <div className="w-10 h-5 bg-[#D2D2D7] rounded-full peer-checked:bg-yellow-500 relative transition-all duration-300">
                  <div className="absolute left-1 top-1 w-3 h-3 bg-white rounded-full transition-transform duration-300 peer-checked:translate-x-5" />
                </div>
                <span className="text-sm font-semibold text-[#86868B] group-hover:text-[#1D1D1F] transition-colors">School</span>
              </label>

              {selectedCountry2 && (
                <div className="flex items-center gap-2 bg-[#F5F5F7] p-1 rounded-xl border border-[#D2D2D7]/30">
                  <button 
                    onClick={() => setComparisonFilter('all')}
                    className={`px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-lg transition-all ${comparisonFilter === 'all' ? 'bg-white shadow-sm text-[#0071E3]' : 'text-[#86868B]'}`}
                  >
                    All
                  </button>
                  <button 
                    onClick={() => setComparisonFilter('common')}
                    className={`px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-lg transition-all ${comparisonFilter === 'common' ? 'bg-white shadow-sm text-[#0071E3]' : 'text-[#86868B]'}`}
                  >
                    Common
                  </button>
                  <button 
                    onClick={() => setComparisonFilter('unique')}
                    className={`px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-lg transition-all ${comparisonFilter === 'unique' ? 'bg-white shadow-sm text-[#0071E3]' : 'text-[#86868B]'}`}
                  >
                    Unique
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-[#F5F5F7] p-1 rounded-xl border border-[#D2D2D7]/30">
              <button 
                onClick={exportToExcel}
                className="flex items-center gap-2 px-3 py-1.5 hover:bg-white hover:shadow-sm rounded-lg transition-all text-[10px] font-bold text-[#1D1D1F] uppercase tracking-wider"
                title="Export to Excel"
              >
                <Download className="w-3.5 h-3.5 text-green-600" />
                Excel
              </button>
              <button 
                onClick={exportToICal}
                className="flex items-center gap-2 px-3 py-1.5 hover:bg-white hover:shadow-sm rounded-lg transition-all text-[10px] font-bold text-[#1D1D1F] uppercase tracking-wider"
                title="Export to iCal"
              >
                <CalendarIcon className="w-3.5 h-3.5 text-blue-600" />
                iCal
              </button>
              <button 
                onClick={() => setShowVacationModal(true)}
                className="flex items-center gap-2 px-3 py-1.5 hover:bg-white hover:shadow-sm rounded-lg transition-all text-[10px] font-bold text-[#1D1D1F] uppercase tracking-wider"
                title="Add Vacation"
              >
                <Sparkles className="w-3.5 h-3.5 text-purple-600" />
                Add Vacation
              </button>
            </div>
            <button 
              onClick={() => setApiSource(apiSource === 'nager' ? 'openholidays' : 'nager')}
              className="flex items-center gap-2 px-4 py-2 bg-[#F5F5F7] hover:bg-[#E8E8ED] rounded-xl transition-all text-[11px] font-bold text-[#1D1D1F] uppercase tracking-widest"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
              {apiSource === 'nager' ? 'Nager.Date' : 'OpenHolidays'}
            </button>
          </div>
        </div>

        {/* Vacation List Section (Always Visible Above Calendar) */}
        {vacations.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            className="mb-12 bg-white p-8 rounded-[32px] border border-white shadow-xl shadow-black/5"
          >
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold flex items-center gap-3">
                <Sparkles className="w-6 h-6 text-purple-600" />
                Planned Vacations
              </h3>
              <div className="text-sm font-bold text-[#86868B] uppercase tracking-widest bg-[#F5F5F7] px-4 py-1.5 rounded-xl">
                Total: {totalVacationDays} Days
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {vacations.map(v => (
                <div key={v.id} className="p-5 bg-purple-50/50 rounded-2xl border border-purple-100 flex items-center justify-between group">
                  <div>
                    <div className="font-bold text-[#1D1D1F]">{v.name}</div>
                    <div className="text-xs text-[#86868B] font-medium mt-1">
                      {new Date(v.startDate).toLocaleDateString()} - {new Date(v.endDate).toLocaleDateString()}
                    </div>
                    <div className="text-[10px] font-bold text-purple-600 uppercase tracking-widest mt-2">
                      {(() => {
                        let count = 0;
                        const start = new Date(v.startDate);
                        const end = new Date(v.endDate);
                        const current = new Date(start);
                        while (current <= end) {
                          const dateStr = formatDate(current);
                          const isWeekend = current.getDay() === 0 || current.getDay() === 6;
                          const isHoliday = holidays.some(h => h.date === dateStr);
                          if (!isWeekend && !isHoliday) count++;
                          current.setDate(current.getDate() + 1);
                        }
                        return `${count} Working Days`;
                      })()}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-all">
                    <button 
                      onClick={() => {
                        setEditingVacation(v);
                        setShowVacationModal(true);
                      }}
                      className="p-2 hover:bg-white rounded-xl text-blue-500"
                    >
                      <FileText className="w-4 h-4" />
                    </button>
                    <button 
                      onClick={() => removeVacation(v.id)}
                      className="p-2 hover:bg-white rounded-xl text-red-500"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
            {totalVacationDays > 30 && (
              <div className="mt-6 flex items-center gap-3 p-4 bg-orange-50 border border-orange-100 rounded-2xl text-orange-700">
                <AlertCircle className="w-5 h-5" />
                <p className="text-sm font-bold uppercase tracking-wider">Warning: You have exceeded 30 vacation days ({totalVacationDays} days total).</p>
              </div>
            )}
          </motion.div>
        )}

        {/* Calendar Views */}
        <AnimatePresence mode="wait">
          {loading ? (
            <motion.div 
              key="loading"
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
              className="py-48 flex flex-col items-center justify-center"
            >
              <div className="relative">
                <Loader2 className="w-12 h-12 text-[#0071E3] animate-spin" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-2 h-2 bg-[#0071E3] rounded-full animate-ping" />
                </div>
              </div>
              <p className="mt-6 text-[#86868B] font-semibold text-lg">Synchronizing global data...</p>
            </motion.div>
          ) : viewMode === 'year' ? (
            <div className="space-y-12">
              <motion.div 
                key="year-view"
                initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.98 }}
                className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-10"
              >
                {Array.from({ length: 12 }).map((_, m) => {
                  const monthDays = generateMonthDays(selectedYear, m);
                  const firstDayPadding = (new Date(selectedYear, m, 1).getDay() + 6) % 7;
                  const cells = [...Array(firstDayPadding).fill(null), ...monthDays];
                  const weeks = [];
                  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));

                  return (
                    <div key={m} className="bg-white p-8 rounded-[32px] border border-white shadow-lg shadow-black/5 hover:shadow-xl transition-all duration-500 group">
                      <h3 className="text-lg font-bold text-[#1D1D1F] mb-6 flex items-center justify-between">
                        {new Date(selectedYear, m).toLocaleString('default', { month: 'long' })}
                        <span className="text-[11px] text-[#86868B] font-bold uppercase tracking-widest bg-[#F5F5F7] px-2 py-1 rounded-md">Q{Math.floor(m / 3) + 1}</span>
                      </h3>
                      <div className="grid grid-cols-[20px_repeat(7,1fr)] gap-2 text-center items-center">
                        <div className="text-[9px] font-bold text-[#D2D2D7] mb-3">KW</div>
                        {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((d, i) => (
                          <div key={`${m}-${d}-${i}`} className="text-[10px] font-bold text-[#86868B] mb-3">{d}</div>
                        ))}
                        {weeks.map((week, wIdx) => {
                          const firstDay = week.find(d => d !== null);
                          const kw = firstDay ? firstDay.weekNumber : getWeekNumber(new Date(selectedYear, m, wIdx * 7 - firstDayPadding + 1));
                          
                          return (
                            <React.Fragment key={wIdx}>
                              <div className="text-[9px] font-bold text-[#D2D2D7]">{kw}</div>
                              {week.map((day, dIdx) => (
                                day ? (
                                  <button 
                                    key={formatDate(day.date)}
                                    onClick={() => {
                                      setSelectedMonth(m);
                                      setViewMode('month');
                                    }}
                                    title={day.holidayName || day.vacationName}
                                    className={`
                                      aspect-square flex items-center justify-center text-xs rounded-xl transition-all relative group/day
                                      ${day.isHoliday && showHolidays ? 'bg-blue-50 text-[#0071E3] font-bold ring-1 ring-blue-100' : ''}
                                      ${day.isBridgeDay && showBridgeDays ? 'bg-green-50 text-[#34C759] font-bold ring-1 ring-green-100' : ''}
                                      ${day.isVacation && showVacations ? 'bg-purple-50 text-purple-600 font-bold ring-1 ring-purple-100' : ''}
                                      ${day.isSchoolHoliday && showSchoolHolidays ? 'bg-yellow-50 text-yellow-700 font-bold ring-1 ring-yellow-100' : ''}
                                      ${day.isWeekend && showWeekends ? 'bg-orange-50/50 text-orange-600/70' : day.isWeekend ? 'text-[#86868B]/40' : 'text-[#1D1D1F]'}
                                      ${!day.isHoliday && !day.isBridgeDay && !day.isVacation && !day.isSchoolHoliday && !day.isWeekend ? 'hover:bg-[#F5F5F7]' : ''}
                                    `}
                                  >
                                    {day.date.getDate()}
                                    {(day.isHoliday && showHolidays) && <div className="absolute -top-1 -right-1 w-2 h-2 bg-[#0071E3] rounded-full border-2 border-white" />}
                                    {(day.isVacation && showVacations) && <div className="absolute -top-1 -right-1 w-2 h-2 bg-purple-500 rounded-full border-2 border-white" />}
                                    {(day.isSchoolHoliday && showSchoolHolidays) && <div className="absolute -top-1 -right-1 w-2 h-2 bg-yellow-500 rounded-full border-2 border-white" />}
                                  </button>
                                ) : (
                                  <div key={`empty-${wIdx}-${dIdx}`} />
                                )
                              ))}
                            </React.Fragment>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </motion.div>
            </div>
          ) : viewMode === 'month' ? (
            <motion.div 
              key="month-view"
              initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
              className="bg-white rounded-[48px] border border-white shadow-2xl shadow-black/5 overflow-hidden"
            >
              <div className="p-10 border-b border-[#D2D2D7]/30 flex items-center justify-between bg-[#FBFBFD]/50 backdrop-blur-md">
                <div className="flex items-center gap-8">
                  <h2 className="text-4xl font-bold tracking-tight">
                    {new Date(selectedYear, selectedMonth).toLocaleString('default', { month: 'long' })}
                    <span className="text-[#86868B] font-medium ml-4">{selectedYear}</span>
                  </h2>
                  <div className="flex items-center gap-2 bg-white p-1.5 rounded-2xl border border-[#D2D2D7]/50 shadow-sm">
                    <button onClick={() => setSelectedMonth(m => m === 0 ? 11 : m - 1)} className="p-2.5 hover:bg-[#F5F5F7] rounded-xl transition-all active:scale-90"><ChevronLeft className="w-5 h-5" /></button>
                    <button onClick={() => setSelectedMonth(m => m === 11 ? 0 : m + 1)} className="p-2.5 hover:bg-[#F5F5F7] rounded-xl transition-all active:scale-90"><ChevronRight className="w-5 h-5" /></button>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <div className="text-[11px] font-bold text-[#86868B] uppercase tracking-[0.2em]">
                    {countryName} {countryName2 ? `vs ${countryName2}` : ''}
                  </div>
                  <div className="text-[10px] font-medium text-[#D2D2D7]">
                    Source: {apiSource === 'nager' ? 'Nager.Date' : 'OpenHolidays'}
                  </div>
                </div>
              </div>

              <div className="flex flex-col divide-y divide-[#D2D2D7]/20">
                {generateMonthDays(selectedYear, selectedMonth).map((day, idx) => (
                  <div 
                    key={formatDate(day.date)}
                    className={`
                      flex items-center px-10 py-8 transition-all group relative
                      ${day.isHoliday && showHolidays ? 'bg-blue-50/20' : ''}
                      ${day.isBridgeDay && showBridgeDays ? 'bg-green-50/20' : ''}
                      ${day.isWeekend && showWeekends ? 'bg-orange-50/10' : day.isWeekend ? 'bg-[#FBFBFD]/50' : ''}
                      hover:bg-[#F5F5F7]/50
                    `}
                  >
                    {/* Week Number & Weekday (Side) */}
                    <div className="w-32 flex flex-col">
                      <span className="text-[11px] font-bold text-[#86868B] uppercase tracking-widest mb-1">KW {day.weekNumber}</span>
                      <span className={`text-base font-bold tracking-tight ${day.isWeekend ? 'text-[#86868B]' : 'text-[#1D1D1F]'}`}>
                        {day.date.toLocaleString('default', { weekday: 'long' })}
                      </span>
                    </div>

                    {/* Date Number */}
                    <div className="w-24 flex items-center justify-center">
                      <div className={`
                        w-14 h-14 rounded-2xl flex items-center justify-center text-3xl font-bold transition-all
                        ${day.isHoliday && showHolidays ? 'bg-blue-100 text-[#0071E3] shadow-sm' : 
                          day.isBridgeDay && showBridgeDays ? 'bg-green-100 text-[#34C759] shadow-sm' : 
                          day.isWeekend && showWeekends ? 'bg-orange-100 text-orange-600 shadow-sm' :
                          'text-[#1D1D1F]'}
                      `}>
                        {day.date.getDate()}
                      </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 px-12">
                      {day.isHoliday && showHolidays ? (
                        <div className="flex flex-col gap-3">
                          {day.holidays?.map((h, i) => (
                            <div key={i} className="flex items-center gap-5">
                              <div className={`w-12 h-12 ${h.countryCode === selectedCountry ? 'bg-blue-100/50' : 'bg-purple-100/50'} rounded-2xl flex items-center justify-center`}>
                                <CalendarIcon className={`w-6 h-6 ${h.countryCode === selectedCountry ? 'text-[#0071E3]' : 'text-purple-600'}`} />
                              </div>
                              <div>
                                <div className="text-xl font-bold text-[#1D1D1F] mb-0.5">
                                  {h.name} 
                                  {selectedCountry2 && <span className="ml-2 text-xs font-bold text-[#86868B] uppercase tracking-widest bg-[#F5F5F7] px-2 py-0.5 rounded">{h.countryCode}</span>}
                                </div>
                                <div className={`text-[11px] font-bold ${h.countryCode === selectedCountry ? 'text-[#0071E3]' : 'text-purple-600'} uppercase tracking-[0.15em]`}>Official Public Holiday</div>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : day.isVacation && showVacations ? (
                        <div className="flex items-center gap-5">
                          <div className="w-12 h-12 bg-purple-100/50 rounded-2xl flex items-center justify-center">
                            <Sparkles className="w-6 h-6 text-purple-600" />
                          </div>
                          <div>
                            <div className="text-xl font-bold text-[#1D1D1F] mb-0.5">{day.vacationName}</div>
                            <div className="text-[11px] font-bold text-purple-600 uppercase tracking-[0.15em]">Personal Vacation</div>
                          </div>
                        </div>
                      ) : day.isBridgeDay && showBridgeDays ? (
                        <div className="flex flex-col gap-3">
                          {day.bridgeDayCountries?.map((code, i) => {
                            const isPrimary = code === selectedCountry;
                            const cName = COUNTRIES.find(c => c.code === code)?.name || code;
                            return (
                              <div key={i} className="flex items-center gap-5">
                                <div className={`w-12 h-12 ${isPrimary ? 'bg-green-100/50' : 'bg-emerald-100/50'} rounded-2xl flex items-center justify-center`}>
                                  <Sparkles className={`w-6 h-6 ${isPrimary ? 'text-[#34C759]' : 'text-emerald-600'}`} />
                                </div>
                                <div>
                                  <div className="text-xl font-bold text-[#1D1D1F] mb-0.5">
                                    Strategic Bridge Day
                                    {selectedCountry2 && <span className="ml-2 text-xs font-bold text-[#86868B] uppercase tracking-widest bg-[#F5F5F7] px-2 py-0.5 rounded">{code}</span>}
                                  </div>
                                  <div className={`text-[11px] font-bold ${isPrimary ? 'text-[#34C759]' : 'text-emerald-600'} uppercase tracking-[0.15em]`}>
                                    Optimized for {cName}
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      ) : day.isWeekend ? (
                        <div className="flex items-center gap-5 opacity-60">
                          <div className="w-12 h-12 bg-orange-100/30 rounded-2xl flex items-center justify-center"><CalendarDays className="w-6 h-6 text-orange-400" /></div>
                          <div>
                            <div className="text-lg font-bold text-[#86868B]">Weekend</div>
                            <div className="text-[11px] font-bold text-[#86868B] uppercase tracking-[0.2em]">Non-Working Day</div>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-center gap-4 opacity-0 group-hover:opacity-100 transition-all duration-500 translate-x-4 group-hover:translate-x-0">
                          <div className="w-1 h-1 bg-[#D2D2D7] rounded-full" />
                          <span className="text-sm font-semibold text-[#86868B]">Standard Business Day</span>
                        </div>
                      )}
                    </div>

                    {/* Action */}
                    <div className="w-16 flex justify-end">
                      <button className="p-3 hover:bg-white rounded-2xl transition-all shadow-sm opacity-0 group-hover:opacity-100 translate-x-4 group-hover:translate-x-0">
                        <ArrowRight className="w-5 h-5 text-[#0071E3]" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          ) : (
            <motion.div 
              key="list-view"
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
              className="bg-white rounded-[40px] border border-white shadow-2xl shadow-black/5 overflow-hidden"
            >
              <div className="p-10 border-b border-[#D2D2D7]/30 bg-[#FBFBFD]/50 flex items-center justify-between">
                <h2 className="text-3xl font-bold tracking-tight flex items-center gap-4">
                  <ListIcon className="w-8 h-8 text-[#0071E3]" />
                  Yearly Non-Working Days
                  <span className="text-[#86868B] font-medium text-xl">{selectedYear}</span>
                </h2>
                <div className="px-4 py-2 bg-blue-50 rounded-2xl text-[#0071E3] font-bold text-sm">
                  {yearlyData.length} Total Days Found
                </div>
              </div>
              
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-[#F5F5F7]/50 border-b border-[#D2D2D7]/30">
                      <th className="px-10 py-5 text-[11px] font-bold text-[#86868B] uppercase tracking-widest">Date</th>
                      <th className="px-10 py-5 text-[11px] font-bold text-[#86868B] uppercase tracking-widest">Weekday</th>
                      <th className="px-10 py-5 text-[11px] font-bold text-[#86868B] uppercase tracking-widest">Type</th>
                      {selectedCountry2 && <th className="px-10 py-5 text-[11px] font-bold text-[#86868B] uppercase tracking-widest">Country</th>}
                      <th className="px-10 py-5 text-[11px] font-bold text-[#86868B] uppercase tracking-widest">Description</th>
                      <th className="px-10 py-5 text-[11px] font-bold text-[#86868B] uppercase tracking-widest">KW</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#D2D2D7]/20">
                    {yearlyData.map((day, idx) => (
                      <tr key={idx} className="hover:bg-[#F5F5F7]/30 transition-colors group">
                        <td className="px-10 py-6 font-bold text-[#1D1D1F]">
                          {day.date.toLocaleDateString('default', { day: '2-digit', month: '2-digit', year: 'numeric' })}
                        </td>
                        <td className="px-10 py-6 text-[#86868B] font-medium">
                          {day.date.toLocaleString('default', { weekday: 'long' })}
                        </td>
                        <td className="px-10 py-6">
                          <span className={`
                            px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider
                            ${day.isHoliday ? 'bg-blue-100 text-[#0071E3]' : 
                              day.isVacation ? 'bg-purple-100 text-purple-600' :
                              day.isBridgeDay ? 'bg-green-100 text-[#34C759]' : 
                              'bg-orange-100 text-orange-600'}
                          `}>
                            {day.isHoliday ? 'Holiday' : day.isVacation ? 'Vacation' : day.isBridgeDay ? 'Bridge Day' : 'Weekend'}
                          </span>
                        </td>
                        {selectedCountry2 && (
                          <td className="px-10 py-6">
                            <div className="flex flex-col gap-1.5">
                              {day.holidays?.map((h, i) => {
                                const cName = COUNTRIES.find(c => c.code === h.countryCode)?.name || h.countryCode;
                                const isPrimary = h.countryCode === selectedCountry;
                                return (
                                  <span key={i} className={`
                                    px-3 py-1 rounded-lg text-[10px] font-bold uppercase tracking-widest w-fit
                                    ${isPrimary ? 'bg-blue-50 text-[#0071E3] border border-blue-100' : 'bg-purple-50 text-purple-600 border border-purple-100'}
                                  `}>
                                    {cName}
                                  </span>
                                );
                              })}
                              {day.isBridgeDay && day.bridgeDayCountries?.map((code, i) => {
                                const cName = COUNTRIES.find(c => c.code === code)?.name || code;
                                const isPrimary = code === selectedCountry;
                                return (
                                  <span key={i} className={`
                                    px-3 py-1 rounded-lg text-[10px] font-bold uppercase tracking-widest w-fit
                                    ${isPrimary ? 'bg-green-50 text-[#34C759] border border-green-100' : 'bg-emerald-50 text-emerald-600 border border-emerald-100'}
                                  `}>
                                    {cName}
                                  </span>
                                );
                              })}
                              {!day.isHoliday && !day.isBridgeDay && <span className="text-[10px] font-bold text-[#D2D2D7] uppercase tracking-widest">-</span>}
                            </div>
                          </td>
                        )}
                        <td className="px-10 py-6 font-semibold text-[#1D1D1F]">
                          {day.holidayName || day.vacationName || (day.isBridgeDay ? 'Strategic Bridge Day' : 'Weekend')}
                        </td>
                        <td className="px-10 py-6 text-[#86868B] font-bold">
                          {day.weekNumber}
                        </td>
                      </tr>
                    ))}
                    {yearlyData.length === 0 && (
                      <tr>
                        <td colSpan={5} className="px-10 py-20 text-center">
                          <div className="flex flex-col items-center gap-4">
                            <AlertCircle className="w-12 h-12 text-[#D2D2D7]" />
                            <p className="text-lg font-medium text-[#86868B]">No days match your current filter criteria.</p>
                          </div>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Holiday List Summary (Search Results) */}
        {searchTerm && filteredHolidays.length > 0 && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            className="mt-16 bg-white p-10 rounded-[40px] border border-[#D2D2D7]/30 shadow-xl"
          >
            <h3 className="text-2xl font-bold mb-8 flex items-center gap-3">
              <Search className="w-6 h-6 text-[#0071E3]" />
              Search Results for "{searchTerm}"
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredHolidays.map((h, i) => (
                <div key={i} className="p-6 bg-[#F5F5F7] rounded-3xl border border-[#D2D2D7]/20 hover:border-[#0071E3]/30 transition-all group">
                  <div className="text-[10px] font-bold text-[#0071E3] uppercase tracking-widest mb-2">
                    {new Date(h.date).toLocaleDateString('default', { day: 'numeric', month: 'long', year: 'numeric' })}
                  </div>
                  <div className="font-bold text-lg mb-1 group-hover:text-[#0071E3] transition-colors">{h.name}</div>
                  <div className="text-sm text-[#86868B] italic">{h.localName}</div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </main>

      {/* Chatbot Drawer */}
      <AnimatePresence>
        {isChatOpen && (
          <>
            <motion.div 
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setIsChatOpen(false)}
              className="fixed inset-0 bg-black/30 backdrop-blur-md z-[60]"
            />
            <motion.div 
              initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 30, stiffness: 300 }}
              className="fixed right-0 top-0 bottom-0 w-full max-w-lg bg-white shadow-2xl z-[70] flex flex-col border-l border-[#D2D2D7]/30"
            >
              <div className="p-8 border-b border-[#D2D2D7]/30 flex items-center justify-between bg-[#FBFBFD]/80 backdrop-blur-md">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-blue-50 rounded-2xl flex items-center justify-center shadow-inner">
                    <Sparkles className="w-6 h-6 text-[#0071E3]" />
                  </div>
                  <div>
                    <h3 className="font-bold text-lg tracking-tight">Vacation Assistant</h3>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-[#34C759] rounded-full animate-pulse" />
                      <span className="text-[11px] font-bold text-[#86868B] uppercase tracking-[0.2em]">Gemini 3.1 Pro Online</span>
                    </div>
                  </div>
                </div>
                <button onClick={() => setIsChatOpen(false)} className="p-3 hover:bg-[#F5F5F7] rounded-full transition-all active:scale-90"><X className="w-6 h-6 text-[#86868B]" /></button>
              </div>

              <div className="flex-1 overflow-y-auto p-8 space-y-8 scroll-smooth">
                {chatMessages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`
                      max-w-[90%] p-5 rounded-[28px] text-[15px] leading-relaxed shadow-sm
                      ${msg.role === 'user' ? 
                        'bg-[#0071E3] text-white rounded-tr-none' : 
                        'bg-[#F5F5F7] text-[#1D1D1F] rounded-tl-none border border-[#D2D2D7]/30'}
                    `}>
                      <div className="markdown-body prose prose-sm max-w-none">
                        <Markdown>{msg.text}</Markdown>
                      </div>
                    </div>
                  </div>
                ))}
                {isChatLoading && (
                  <div className="flex justify-start">
                    <div className="bg-[#F5F5F7] p-5 rounded-[28px] rounded-tl-none border border-[#D2D2D7]/30 flex items-center gap-3 shadow-sm">
                      <div className="flex gap-1">
                        <div className="w-1.5 h-1.5 bg-[#0071E3] rounded-full animate-bounce [animation-delay:-0.3s]" />
                        <div className="w-1.5 h-1.5 bg-[#0071E3] rounded-full animate-bounce [animation-delay:-0.15s]" />
                        <div className="w-1.5 h-1.5 bg-[#0071E3] rounded-full animate-bounce" />
                      </div>
                      <span className="text-xs font-bold text-[#86868B] uppercase tracking-widest">Analyzing Data...</span>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              <div className="p-8 border-t border-[#D2D2D7]/30 bg-[#FBFBFD]/80 backdrop-blur-md">
                <div className="relative group">
                  <input 
                    type="text" 
                    value={chatInput}
                    onChange={e => setChatInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSendMessage()}
                    placeholder="Ask about holiday planning or bridge days..."
                    className="w-full bg-white border border-[#D2D2D7] rounded-2xl pl-6 pr-14 py-4 text-base focus:ring-4 focus:ring-blue-500/10 outline-none transition-all shadow-sm group-hover:border-[#0071E3]/50"
                  />
                  <button 
                    onClick={handleSendMessage}
                    disabled={isChatLoading || !chatInput.trim()}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 p-2.5 bg-[#0071E3] text-white rounded-xl disabled:opacity-50 transition-all hover:scale-105 active:scale-95 shadow-lg shadow-blue-500/20"
                  >
                    <Send className="w-5 h-5" />
                  </button>
                </div>
                <div className="flex items-center justify-center gap-2 mt-4">
                  <Sparkles className="w-3 h-3 text-[#86868B]" />
                  <p className="text-[10px] text-[#86868B] font-bold uppercase tracking-widest">Powered by Google Gemini Intelligence</p>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Vacation Modal */}
      <AnimatePresence>
        {showVacationModal && (
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-[110] flex items-center justify-center p-6 bg-black/20 backdrop-blur-sm"
            onClick={() => {
              setShowVacationModal(false);
              setEditingVacation(null);
            }}
          >
            <motion.div 
              initial={{ opacity: 0, scale: 0.9, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="bg-white w-full max-w-md rounded-[40px] shadow-2xl overflow-hidden p-10"
              onClick={e => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-8">
                <h2 className="text-2xl font-bold tracking-tight">{editingVacation ? 'Edit Vacation' : 'Add Vacation'}</h2>
                <button 
                  onClick={() => {
                    setShowVacationModal(false);
                    setEditingVacation(null);
                  }} 
                  className="p-2 hover:bg-[#F5F5F7] rounded-full transition-all"
                >
                  <X className="w-6 h-6 text-[#86868B]" />
                </button>
              </div>
              
              <form onSubmit={(e) => {
                e.preventDefault();
                const formData = new FormData(e.currentTarget);
                const v = {
                  name: formData.get('name') as string,
                  startDate: formData.get('startDate') as string,
                  endDate: formData.get('endDate') as string,
                };
                if (editingVacation) {
                  updateVacation({ ...v, id: editingVacation.id });
                } else {
                  addVacation(v);
                }
                setShowVacationModal(false);
                setEditingVacation(null);
              }} className="space-y-6">
                <div className="space-y-2">
                  <label className="text-xs font-bold text-[#86868B] uppercase tracking-widest">Vacation Name</label>
                  <input 
                    name="name" 
                    required 
                    type="text" 
                    defaultValue={editingVacation?.name}
                    placeholder="Summer Trip" 
                    className="w-full px-4 py-3 bg-[#F5F5F7] rounded-xl border border-[#D2D2D7]/30 outline-none focus:ring-2 focus:ring-purple-500/20" 
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-xs font-bold text-[#86868B] uppercase tracking-widest">Start Date</label>
                    <input 
                      name="startDate" 
                      required 
                      type="date" 
                      defaultValue={editingVacation?.startDate}
                      onChange={(e) => setVacationForm(prev => ({ ...prev, startDate: e.target.value }))}
                      className="w-full px-4 py-3 bg-[#F5F5F7] rounded-xl border border-[#D2D2D7]/30 outline-none focus:ring-2 focus:ring-purple-500/20" 
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-bold text-[#86868B] uppercase tracking-widest">End Date</label>
                    <input 
                      name="endDate" 
                      required 
                      type="date" 
                      defaultValue={editingVacation?.endDate}
                      onChange={(e) => setVacationForm(prev => ({ ...prev, endDate: e.target.value }))}
                      className="w-full px-4 py-3 bg-[#F5F5F7] rounded-xl border border-[#D2D2D7]/30 outline-none focus:ring-2 focus:ring-purple-500/20" 
                    />
                  </div>
                </div>
                
                {(vacationForm.startDate && vacationForm.endDate) && (
                  <div className="p-4 bg-purple-50 rounded-2xl border border-purple-100">
                    <div className="text-[10px] font-bold text-purple-600 uppercase tracking-widest mb-1">Calculation Preview</div>
                    <div className="text-lg font-bold text-purple-700">
                      {calculateWorkingDays(vacationForm.startDate, vacationForm.endDate)} Working Days
                    </div>
                    <p className="text-[10px] text-purple-400 mt-1 italic">Excluding weekends and public holidays</p>
                  </div>
                )}

                <button type="submit" className="w-full py-4 bg-purple-600 text-white font-bold rounded-2xl hover:bg-purple-700 transition-all shadow-lg shadow-purple-500/20">
                  {editingVacation ? 'Save Changes' : 'Add Vacation'}
                </button>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Help Modal */}
        <AnimatePresence>
          {showHelp && (
            <motion.div 
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-black/20 backdrop-blur-sm"
              onClick={() => setShowHelp(false)}
            >
              <motion.div 
                initial={{ opacity: 0, scale: 0.9, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.9, y: 20 }}
                className="bg-white w-full max-w-2xl rounded-[40px] shadow-2xl overflow-hidden"
                onClick={e => e.stopPropagation()}
              >
                <div className="p-8 border-b border-[#D2D2D7]/30 flex items-center justify-between bg-[#FBFBFD]">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-blue-50 rounded-2xl flex items-center justify-center">
                      <HelpCircle className="w-6 h-6 text-[#0071E3]" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold tracking-tight">Help & Documentation</h2>
                      <p className="text-sm text-[#86868B]">Learn how to use Thomas Vacation Finder</p>
                    </div>
                  </div>
                  <button onClick={() => setShowHelp(false)} className="p-2 hover:bg-[#F5F5F7] rounded-full transition-all"><X className="w-6 h-6 text-[#86868B]" /></button>
                </div>
                
                <div className="p-10 max-h-[70vh] overflow-y-auto space-y-8">
                  <section>
                    <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                      <Globe className="w-5 h-5 text-[#0071E3]" />
                      Global Coverage
                    </h3>
                    <p className="text-[#1D1D1F] leading-relaxed">
                      Select any country and year to instantly retrieve public holidays. We use high-reliability APIs (Nager.Date and OpenHolidays) to ensure accurate data for business planning.
                    </p>
                  </section>

                  <section>
                    <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                      <Maximize2 className="w-5 h-5 text-[#34C759]" />
                      View Modes
                    </h3>
                    <ul className="space-y-3 text-[#1D1D1F]">
                      <li className="flex gap-3">
                        <strong className="min-w-[80px]">Year:</strong> A bird's-eye view of all 12 months. Perfect for identifying long-term patterns.
                      </li>
                      <li className="flex gap-3">
                        <strong className="min-w-[80px]">Month:</strong> Detailed daily breakdown with week numbers (KW) and specific holiday names.
                      </li>
                      <li className="flex gap-3">
                        <strong className="min-w-[80px]">List:</strong> A searchable, sortable table of all non-working days in the selected year.
                      </li>
                    </ul>
                  </section>

                  <section>
                    <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                      <Sparkles className="w-5 h-5 text-[#FF9500]" />
                      Strategic Insights
                    </h3>
                    <p className="text-[#1D1D1F] leading-relaxed mb-4">
                      Toggle <strong>Bridge Days</strong> to find "Strategic Windows"—days between holidays and weekends that can be used to maximize time off or optimize business operations.
                    </p>
                    <div className="bg-[#F5F5F7] p-4 rounded-2xl border border-[#D2D2D7]/30">
                      <p className="text-xs font-semibold text-[#86868B] uppercase tracking-wider mb-2">Pro Tip</p>
                      <p className="text-sm italic">Use the "Vacation Assistant" (AI Chat) to ask for specific travel or project planning advice based on the current calendar data.</p>
                    </div>
                  </section>

                  <section>
                    <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                      <Download className="w-5 h-5 text-green-600" />
                      Exporting Data
                    </h3>
                    <p className="text-[#1D1D1F] leading-relaxed">
                      Export your filtered list to <strong>Excel (.xlsx)</strong> for data analysis or <strong>iCal (.ics)</strong> to sync directly with Outlook, Apple Calendar, or Google Calendar.
                    </p>
                  </section>
                </div>

                <div className="p-8 bg-[#FBFBFD] border-t border-[#D2D2D7]/30 text-center">
                  <button 
                    onClick={() => setShowHelp(false)}
                    className="px-8 py-3 bg-[#0071E3] text-white font-bold rounded-2xl hover:bg-[#0077ED] transition-all shadow-lg shadow-blue-500/20"
                  >
                    Got it, thanks!
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

      {/* Global Footer */}
      <footer className="bg-white border-t border-[#D2D2D7]/30 py-20 mt-32">
        <div className="max-w-[1400px] mx-auto px-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-16">
            <div className="col-span-2">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 bg-[#0071E3] rounded-xl flex items-center justify-center">
                  <Briefcase className="w-6 h-6 text-white" />
                </div>
                <span className="font-bold text-2xl tracking-tight">Thomas Vacation Finder (for Exyte......)</span>
              </div>
              <p className="text-[#86868B] text-lg max-w-md leading-relaxed">
                The definitive platform for global team coordination. Optimize your business timeline with precision.
              </p>
            </div>
            <div className="space-y-4">
              <h4 className="text-xs font-bold text-[#1D1D1F] uppercase tracking-[0.2em]">Resources</h4>
              <ul className="space-y-3 text-sm font-medium text-[#86868B]">
                <li><a href="#" className="hover:text-[#0071E3] transition-colors">Global API</a></li>
                <li><a href="#" className="hover:text-[#0071E3] transition-colors">Documentation</a></li>
                <li><a href="#" className="hover:text-[#0071E3] transition-colors">Team Planning</a></li>
              </ul>
            </div>
            <div className="space-y-4">
              <h4 className="text-xs font-bold text-[#1D1D1F] uppercase tracking-[0.2em]">Legal</h4>
              <ul className="space-y-3 text-sm font-medium text-[#86868B]">
                <li><a href="#" className="hover:text-[#0071E3] transition-colors">Privacy Policy</a></li>
                <li><a href="#" className="hover:text-[#0071E3] transition-colors">Terms of Service</a></li>
                <li><a href="#" className="hover:text-[#0071E3] transition-colors">Cookie Settings</a></li>
              </ul>
            </div>
          </div>
          <div className="pt-12 border-t border-[#D2D2D7]/30 flex flex-col md:flex-row justify-between items-center gap-6">
            <p className="text-[11px] font-bold text-[#86868B] uppercase tracking-widest">© {new Date().getFullYear()} Thomas Vacation Finder. All rights reserved.</p>
            <div className="flex items-center gap-6">
              <Globe className="w-4 h-4 text-[#86868B]" />
              <span className="text-[11px] font-bold text-[#86868B] uppercase tracking-widest">Global • English</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
