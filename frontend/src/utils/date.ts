import { isValidJalaaliDate, toGregorian, toJalaali } from "./jalaali";
import { toEnglishDigits } from "./format";
export type CalendarMode = "jalali" | "gregorian";
const pad = (value: number) => String(value).padStart(2, "0");
export function gregorianToJalali(iso: string) { const [gy, gm, gd] = iso.slice(0, 10).split("-").map(Number); if (!gy || !gm || !gd) return ""; const j = toJalaali(gy, gm, gd); return `${j.jy}/${pad(j.jm)}/${pad(j.jd)}`; }
export function jalaliToGregorian(value: string) { const [jy, jm, jd] = toEnglishDigits(value).replace(/-/g, "/").split("/").map(Number); if (!isValidJalaaliDate(jy, jm, jd)) throw new Error("تاریخ شمسی معتبر نیست."); const g = toGregorian(jy, jm, jd); return `${g.gy}-${pad(g.gm)}-${pad(g.gd)}`; }
export function formatDate(value: string | null | undefined, mode: CalendarMode = "jalali") { if (!value) return "—"; const iso = value.slice(0, 10); return mode === "jalali" ? gregorianToJalali(iso) : iso; }
export function todayIso() { return new Date().toISOString().slice(0, 10); }
