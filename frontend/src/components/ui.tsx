import { useEffect, useId, useRef, useState, type FormEvent, type InputHTMLAttributes, type ReactNode } from "react";
import { usePreferences } from "../theme/ThemeContext";
import { formatDate, gregorianToJalali, jalaliToGregorian } from "../utils/date";
import { formatMoney, statusLabel } from "../utils/format";

export function PageHeader({ title, description, action }: { title: string; description?: ReactNode; action?: ReactNode }) { return <header className="page-header"><div><h1>{title}</h1>{description && <p>{description}</p>}</div>{action}</header>; }
export function Card({ title, children, className = "" }: { title?: string; children: ReactNode; className?: string }) { return <section className={`card ${className}`}>{title && <h2 className="card-title">{title}</h2>}{children}</section>; }
export function LoadingState({ label = "در حال دریافت اطلاعات…" }: { label?: string }) { return <div className="state" role="status"><span className="spinner" />{label}</div>; }
export function EmptyState({ title = "اطلاعاتی ثبت نشده است", detail }: { title?: string; detail?: string }) { return <div className="state state--empty"><span className="state-icon" aria-hidden>□</span><strong>{title}</strong>{detail && <small>{detail}</small>}</div>; }
export function ErrorState({ message, retry }: { message: string; retry?: () => void }) { return <div className="state state--error" role="alert"><strong>دریافت اطلاعات ناموفق بود</strong><span>{message}</span>{retry && <button className="button button--secondary" onClick={retry}>تلاش دوباره</button>}</div>; }
export function StatusBadge({ value }: { value: string }) { const danger = ["CANCELLED", "OVERDUE", "BOUNCED", "HIGH", "INACTIVE"].includes(value.toUpperCase()); const warn = ["DRAFT", "PENDING", "PARTIALLY_PAID", "MEDIUM"].includes(value.toUpperCase()); return <span className={`badge ${danger ? "badge--danger" : warn ? "badge--warning" : "badge--success"}`}>{statusLabel(value)}</span>; }
export function Money({ value, suffix = "ریال" }: { value: string | number; suffix?: string }) { return <span className={Number(value) < 0 ? "negative money" : "money"} dir="ltr">{formatMoney(value)} <small>{suffix}</small></span>; }
export function DateText({ value }: { value: string | null | undefined }) { const { calendar } = usePreferences(); return <time dateTime={value ?? undefined} dir="ltr">{formatDate(value, calendar)}</time>; }
export function Field({ label, hint, error, children }: { label: string; hint?: string; error?: string; children: ReactNode }) { return <label className={`field ${error ? "field--error" : ""}`}><span>{label}</span>{children}{hint && <small>{hint}</small>}{error && <small role="alert">{error}</small>}</label>; }
export const normalizeMoneyInput = (value: string) => {
  const ascii = value.replace(/[۰-۹]/g, (digit) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(digit))).replace(/[٠-٩]/g, (digit) => String("٠١٢٣٤٥٦٧٨٩".indexOf(digit)));
  const cleaned = ascii.replace(/٫/g, ".").replace(/[,٬\s]/g, "").replace(/[^\d.]/g, "");
  const [whole = "", ...fractions] = cleaned.split(".");
  return fractions.length ? `${whole || "0"}.${fractions.join("").slice(0, 2)}` : whole;
};
export const formatMoneyInput = (value: string | number | null | undefined) => {
  const normalized = normalizeMoneyInput(String(value ?? ""));
  if (!normalized) return "";
  const [whole, fraction] = normalized.split(".");
  const grouped = whole.replace(/^0+(?=\d)/, "").replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return fraction === undefined ? grouped : `${grouped}.${fraction}`;
};
type MoneyInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "value" | "defaultValue" | "onChange" | "name"> & {
  name?: string;
  value?: string | number | null;
  defaultValue?: string | number | null;
  onValueChange?: (value: string) => void;
};
export function MoneyInput({ name, value, defaultValue, onValueChange, ...props }: MoneyInputProps) {
  const controlled = value !== undefined;
  const [internal, setInternal] = useState(() => normalizeMoneyInput(String(defaultValue ?? "")));
  const raw = controlled ? normalizeMoneyInput(String(value ?? "")) : internal;
  const change = (next: string) => {
    const normalized = normalizeMoneyInput(next);
    if (!controlled) setInternal(normalized);
    onValueChange?.(normalized);
  };
  return <><input {...props} type="text" inputMode="decimal" dir="ltr" value={formatMoneyInput(raw)} onChange={(event) => change(event.target.value)} />{name && <input type="hidden" name={name} value={raw} />}</>;
}
export function DateField({ label, value, onChange, required }: { label: string; value: string; onChange: (iso: string) => void; required?: boolean }) { const { calendar } = usePreferences(); const [text, setText] = useState(calendar === "jalali" && value ? gregorianToJalali(value) : value); const [error, setError] = useState(""); useEffect(() => setText(calendar === "jalali" && value ? gregorianToJalali(value) : value), [calendar, value]);
  const change = (next: string) => { setText(next); setError(""); if (calendar === "gregorian") { onChange(next); return; } try { if (next.length >= 8) onChange(jalaliToGregorian(next)); } catch (reason) { setError(reason instanceof Error ? reason.message : "تاریخ نامعتبر است."); } };
  return <Field label={`${label} (${calendar === "jalali" ? "شمسی" : "میلادی"})`} error={error}><input type={calendar === "gregorian" ? "date" : "text"} dir="ltr" placeholder={calendar === "jalali" ? "1405/01/01" : undefined} value={text} onChange={(e) => change(e.target.value)} required={required} /></Field>;
}
export function Modal({ open, title, children, onClose, wide = false }: { open: boolean; title: string; children: ReactNode; onClose: () => void; wide?: boolean }) { const titleId = useId(); const dialog = useRef<HTMLElement>(null); useEffect(() => { if (!open) return; const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null; const focusable = () => Array.from(dialog.current?.querySelectorAll<HTMLElement>("button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], [tabindex]:not([tabindex=\"-1\"])") ?? []); focusable()[0]?.focus(); const key = (e: KeyboardEvent) => { if (e.key === "Escape") { onClose(); return; } if (e.key !== "Tab") return; const items = focusable(); if (!items.length) { e.preventDefault(); dialog.current?.focus(); return; } const first = items[0]; const last = items[items.length - 1]; if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); } else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); } }; addEventListener("keydown", key); return () => { removeEventListener("keydown", key); previous?.focus(); }; }, [open, onClose]); if (!open) return null; return <div className="modal-backdrop" onMouseDown={(e) => { if (e.currentTarget === e.target) onClose(); }}><section ref={dialog} tabIndex={-1} className={`modal ${wide ? "modal--wide" : ""}`} role="dialog" aria-modal="true" aria-labelledby={titleId}><header><h2 id={titleId}>{title}</h2><button type="button" className="icon-button" onClick={onClose} aria-label="بستن">×</button></header>{children}</section></div>; }
export function Confirm({ open, title, message, confirmLabel, onConfirm, onClose, busy }: { open: boolean; title: string; message: string; confirmLabel: string; onConfirm: () => void; onClose: () => void; busy?: boolean }) { return <Modal open={open} title={title} onClose={onClose}><p>{message}</p><div className="form-actions"><button className="button button--secondary" onClick={onClose}>انصراف</button><button className="button button--danger" disabled={busy} onClick={onConfirm}>{busy ? "در حال انجام…" : confirmLabel}</button></div></Modal>; }
export function SubmitForm({ children, onSubmit, className = "" }: { children: ReactNode; onSubmit: (event: FormEvent<HTMLFormElement>) => void; className?: string }) { return <form className={`form ${className}`} onSubmit={onSubmit}>{children}</form>; }
