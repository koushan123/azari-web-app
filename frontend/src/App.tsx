import { useEffect, useState } from "react";

import { getHealth } from "./services/api";
import "./styles.css";

type ConnectionState = "checking" | "connected" | "unavailable";

export default function App() {
  const [connection, setConnection] = useState<ConnectionState>("checking");

  useEffect(() => {
    const controller = new AbortController();
    getHealth(controller.signal)
      .then(() => setConnection("connected"))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setConnection("unavailable");
      });
    return () => controller.abort();
  }, []);

  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">Azari · Intelligent Accounting</p>
        <h1>Financial clarity, with accountable intelligence.</h1>
        <p className="summary">
          Double-entry accounting and four explainable machine-learning workflows,
          designed as one integrated system.
        </p>
        <div className={`status status--${connection}`} role="status">
          <span aria-hidden="true" />
          API {connection}
        </div>
      </section>
      <section className="modules" aria-label="Planned intelligence modules">
        {[
          ["01", "Transaction AI", "TF-IDF classification with confidence review"],
          ["02", "Credit Risk", "Random Forest payment-delay probability"],
          ["03", "Cash Flow", "Time-series forecasts and liquidity warnings"],
          ["04", "Segmentation", "Interpreted K-Means customer and supplier groups"],
        ].map(([number, title, detail]) => (
          <article key={number}>
            <span>{number}</span>
            <h2>{title}</h2>
            <p>{detail}</p>
          </article>
        ))}
      </section>
    </main>
  );
}

