import { createContext, useCallback, useContext, useEffect, useMemo, useState, type MouseEvent, type ReactNode } from "react";
interface RouterValue { path: string; navigate: (path: string, replace?: boolean) => void }
const RouterContext = createContext<RouterValue | null>(null);
export function RouterProvider({ children }: { children: ReactNode }) { const [path, setPath] = useState(location.pathname);
  useEffect(() => { const update = () => setPath(location.pathname); addEventListener("popstate", update); return () => removeEventListener("popstate", update); }, []);
  const navigate = useCallback((next: string, replace = false) => { history[replace ? "replaceState" : "pushState"]({}, "", next); setPath(next); scrollTo({ top: 0 }); }, []);
  return <RouterContext.Provider value={useMemo(() => ({ path, navigate }), [path, navigate])}>{children}</RouterContext.Provider>;
}
export function useRouter() { const value = useContext(RouterContext); if (!value) throw new Error("RouterProvider is missing"); return value; }
export function Link({ to, children, className, onClick, ...props }: { to: string; children: ReactNode; className?: string; onClick?: () => void; [key: string]: unknown }) { const { navigate } = useRouter(); const click = (event: MouseEvent<HTMLAnchorElement>) => { if (!event.defaultPrevented && event.button === 0 && !event.metaKey && !event.ctrlKey) { event.preventDefault(); onClick?.(); navigate(to); } }; return <a href={to} className={className} onClick={click} {...props}>{children}</a>; }
