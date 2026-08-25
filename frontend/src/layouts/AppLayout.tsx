import { useEffect, useRef, useState, type ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";
import { Link, useRouter } from "../routes/router";
import { usePreferences } from "../theme/ThemeContext";

interface NavItem { label: string; path: string; permission?: string }
interface NavGroup { label: string; items: NavItem[] }
export const navigation: Array<NavItem | NavGroup> = [
  { label: "داشبورد", path: "/dashboard", permission: "reports:read" },
  { label: "حسابداری", items: [
    { label: "طرف حساب‌ها", path: "/parties", permission: "parties:read" }, { label: "کالا و خدمات", path: "/products", permission: "products:read" },
    { label: "حساب‌ها و سرفصل‌ها", path: "/accounts", permission: "accounts:read" }, { label: "اسناد حسابداری", path: "/journals", permission: "journals:read" }, { label: "دوره‌های مالی", path: "/periods", permission: "periods:read" },
  ]},
  { label: "فروش و دریافت", items: [{ label: "فاکتورها", path: "/invoices", permission: "invoices:read" }, { label: "پرداخت‌ها", path: "/payments", permission: "payments:read" }] },
  { label: "گزارش‌ها", items: [
    { label: "تراز آزمایشی", path: "/reports/trial-balance", permission: "reports:read" }, { label: "صورت سود و زیان", path: "/reports/income-statement", permission: "reports:read" }, { label: "ترازنامه", path: "/reports/balance-sheet", permission: "reports:read" },
    { label: "درآمدها", path: "/reports/revenue", permission: "reports:read" }, { label: "هزینه‌ها", path: "/reports/expenses", permission: "reports:read" }, { label: "مطالبات", path: "/reports/receivables", permission: "reports:read" },
    { label: "پرداختنی‌ها", path: "/reports/payables", permission: "reports:read" }, { label: "جریان نقدی", path: "/reports/cash-flow", permission: "reports:read" }, { label: "گردش طرف حساب", path: "/reports/party-history", permission: "reports:read" },
  ]},
  { label: "هوش مصنوعی", items: [
    { label: "داشبورد هوش مصنوعی", path: "/ai", permission: "ml:read" }, { label: "طبقه‌بندی تراکنش", path: "/ai/classification", permission: "ml:predict" }, { label: "ریسک تأخیر پرداخت", path: "/ai/risk", permission: "ml:predict" },
    { label: "پیش‌بینی جریان نقدی", path: "/ai/forecast", permission: "ml:predict" }, { label: "بخش‌بندی مشتریان", path: "/ai/segments", permission: "ml:predict" }, { label: "مدیریت مدل‌ها", path: "/ai/models", permission: "ml:manage" },
  ]},
  { label: "مدیریت", items: [{ label: "کاربران", path: "/users", permission: "users:read" }, { label: "تنظیمات نمایش", path: "/settings" }] },
];
export function visibleNavigationPaths(can: (permission: string) => boolean) { return navigation.flatMap((entry) => "path" in entry ? (allowed(entry, can) ? [entry.path] : []) : entry.items.filter((item) => allowed(item, can)).map((item) => item.path)); }

function allowed(item: NavItem, can: (p: string) => boolean) { return !item.permission || can(item.permission); }
function DesktopNavigation() { const { can } = useAuth(); const { path } = useRouter(); return <nav className="desktop-nav" aria-label="پیمایش اصلی">{navigation.map((entry) => "path" in entry ? allowed(entry, can) && <Link key={entry.path} to={entry.path} className={path === entry.path ? "active" : ""}>{entry.label}</Link> : (() => { const items = entry.items.filter((item) => allowed(item, can)); return items.length ? <details className="nav-group" key={entry.label}><summary>{entry.label}<span aria-hidden>⌄</span></summary><div className="nav-menu">{items.map((item) => <Link key={item.path} to={item.path} className={path === item.path ? "active" : ""}>{item.label}</Link>)}</div></details> : null; })())}</nav>; }
function MobileNavigation({ open, close }: { open: boolean; close: () => void }) { const { can } = useAuth(); const { path } = useRouter(); const drawer = useRef<HTMLElement>(null); useEffect(() => { if (open) drawer.current?.focus(); }, [open]); return <><div className={`drawer-backdrop ${open ? "open" : ""}`} onClick={close} /><aside ref={drawer} tabIndex={-1} className={`drawer ${open ? "open" : ""}`} aria-hidden={!open}><header><Brand /><button className="icon-button" onClick={close} aria-label="بستن منو">×</button></header><nav>{navigation.map((entry) => "path" in entry ? allowed(entry, can) && <Link key={entry.path} to={entry.path} onClick={close} className={path === entry.path ? "active" : ""}>{entry.label}</Link> : <section key={entry.label}><h3>{entry.label}</h3>{entry.items.filter((item) => allowed(item, can)).map((item) => <Link key={item.path} to={item.path} onClick={close} className={path === item.path ? "active" : ""}>{item.label}</Link>)}</section>)}</nav></aside></>; }
function Brand() { return <Link to="/dashboard" className="brand"><span aria-hidden>آ</span><strong>حسابداری آذری<small>مدیریت مالی هوشمند</small></strong></Link>; }
export function AppLayout({ children }: { children: ReactNode }) { const [drawer, setDrawer] = useState(false); const [profile, setProfile] = useState(false); const { user, logout } = useAuth(); const { theme, toggleTheme } = usePreferences(); return <div className="app"><header className="topbar"><button className="menu-button" onClick={() => setDrawer(true)} aria-label="باز کردن منو">☰</button><Brand /><DesktopNavigation /><div className="top-actions"><button className="icon-button" onClick={toggleTheme} aria-label={theme === "light" ? "فعال‌کردن حالت تاریک" : "فعال‌کردن حالت روشن"}>{theme === "light" ? "◐" : "☀"}</button><div className="profile"><button className="profile-button" onClick={() => setProfile((v) => !v)} aria-expanded={profile}><span className="avatar">{user?.first_name.slice(0, 1)}</span><span>{user?.first_name} {user?.last_name}<small>{user?.roles.join("، ")}</small></span><span aria-hidden>⌄</span></button>{profile && <div className="profile-menu"><Link to="/settings" onClick={() => setProfile(false)}>تنظیمات نمایش</Link><button onClick={logout}>خروج از حساب</button></div>}</div></div></header><MobileNavigation open={drawer} close={() => setDrawer(false)} /><main className="content">{children}</main><footer>آذری · اطلاعات مالی فقط از سامانه حسابداری خوانده می‌شود.</footer></div>; }
