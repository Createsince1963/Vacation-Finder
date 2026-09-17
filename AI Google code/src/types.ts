export interface Holiday {
  date: string;
  localName: string;
  name: string;
  countryCode: string;
  fixed: boolean;
  global: boolean;
  counties: string[] | null;
  launchYear: number | null;
  types: string[];
}

export interface OpenHoliday {
  id: string;
  startDate: string;
  endDate: string;
  type: string;
  name: { language: string; text: string }[];
  nationwide: boolean;
}

export interface Country {
  code: string;
  name: string;
}

export interface CalendarDay {
  date: Date;
  isHoliday: boolean;
  isBridgeDay: boolean;
  isVacation: boolean;
  isSchoolHoliday: boolean;
  holidayName?: string;
  vacationName?: string;
  schoolHolidayName?: string;
  holidays?: Holiday[];
  bridgeDayCountries?: string[];
  isWeekend: boolean;
  weekNumber: number;
}

export interface Vacation {
  id: string;
  startDate: string;
  endDate: string;
  name: string;
}

export interface Subdivision {
  code: string;
  shortName: string;
  name: { language: string; text: string }[];
}

export interface SchoolHoliday {
  id: string;
  startDate: string;
  endDate: string;
  type: string;
  name: { language: string; text: string }[];
}
