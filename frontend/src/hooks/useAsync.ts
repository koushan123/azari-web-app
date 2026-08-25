import { useCallback, useEffect, useState } from "react";
export function useAsync<T>(loader: () => Promise<T>, dependencies: readonly unknown[] = []) {
  const [data, setData] = useState<T | null>(null); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  const load = useCallback(async () => { setLoading(true); setError(""); try { setData(await loader()); } catch (reason) { setError(reason instanceof Error ? reason.message : "خطای ناشناخته"); } finally { setLoading(false); } }, dependencies); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { void load(); }, [load]);
  return { data, loading, error, reload: load, setData };
}
