import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { CalendarMode } from "../utils/date";
type Theme = "light" | "dark";
export const defaultTheme = (stored: string | null): Theme => stored === "dark" ? "dark" : "light";
export const nextTheme = (theme: Theme): Theme => theme === "light" ? "dark" : "light";
interface Preferences { theme: Theme; calendar: CalendarMode; toggleTheme: () => void; setCalendar: (mode: CalendarMode) => void }
const Context = createContext<Preferences | null>(null);
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => defaultTheme(localStorage.getItem("azari_theme")));
  const [calendar, setCalendarState] = useState<CalendarMode>(() => localStorage.getItem("azari_calendar") === "gregorian" ? "gregorian" : "jalali");
  useEffect(() => { document.documentElement.dataset.theme = theme; document.documentElement.dir = "rtl"; document.documentElement.lang = "fa"; localStorage.setItem("azari_theme", theme); }, [theme]);
  const setCalendar = (mode: CalendarMode) => { localStorage.setItem("azari_calendar", mode); setCalendarState(mode); };
  const value = useMemo(() => ({ theme, calendar, toggleTheme: () => setTheme(nextTheme), setCalendar }), [theme, calendar]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function usePreferences() { const value = useContext(Context); if (!value) throw new Error("ThemeProvider is missing"); return value; }
