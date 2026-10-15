import { AlertCircle, CheckCircle2, Inbox, Search, X } from "lucide-react";
import { Fragment, useEffect, type ReactNode } from "react";
import { initials } from "../utils/format";

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow?: ReactNode; title: ReactNode; description?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}

export function Card({ title, actions, children, flush }: { title?: ReactNode; actions?: ReactNode; children: ReactNode; flush?: boolean }) {
  return (
    <section className="card">
      {(title || actions) && <div className="card-header"><h2>{title}</h2>{actions && <div className="row">{actions}</div>}</div>}
      <div className={`card-body${flush ? " flush" : ""}`}>{children}</div>
    </section>
  );
}

export type Tone = "green" | "amber" | "red" | "blue" | "violet" | "accent" | "gray";

export function Badge({ tone = "gray", dot, children }: { tone?: Tone; dot?: boolean; children: ReactNode }) {
  return <span className={`badge ${tone}`}>{dot && <span className="dot" />}{children}</span>;
}

export function LoadingState({ rows = 4 }: { rows?: number; message?: string }) {
  return (
    <div className="card"><div className="card-body stack" aria-busy="true" aria-live="polite">
      {Array.from({ length: rows }, (_, i) => <div key={i} className="skeleton" style={{ width: `${90 - i * 12}%` }} />)}
    </div></div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return <div className="notice error" role="alert"><AlertCircle />{message}</div>;
}

export function Notice({ tone = "info", children }: { tone?: "info" | "warn" | "error" | "success"; children: ReactNode }) {
  const Icon = tone === "success" ? CheckCircle2 : AlertCircle;
  return <div className={`notice ${tone === "info" ? "" : tone}`} role={tone === "error" ? "alert" : undefined}><Icon /><div>{children}</div></div>;
}

export function EmptyState({ title = "Nothing here yet", message, action }: { title?: string; message?: string; action?: ReactNode }) {
  return (
    <div className="empty">
      <Inbox />
      <strong>{title}</strong>
      {message && <span>{message}</span>}
      {action}
    </div>
  );
}

export function Field({ label, hint, error, children, span }: { label: ReactNode; hint?: ReactNode; error?: string; children: ReactNode; span?: boolean }) {
  return (
    <label className={`field${span ? " span-2" : ""}`}>
      <span>{label}</span>
      {children}
      {hint && !error && <small className="field-hint">{hint}</small>}
      {error && <small className="field-error">{error}</small>}
    </label>
  );
}

export function SearchInput({ value, onChange, placeholder = "Search" }: { value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <div className="search">
      <Search />
      <input className="input" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
    </div>
  );
}

export function Tabs<T extends string>({ tabs, value, onChange }: { tabs: { value: T; label: ReactNode; count?: number }[]; value: T; onChange: (v: T) => void }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((tab) => (
        <button key={tab.value} role="tab" aria-selected={tab.value === value} className={`tab${tab.value === value ? " on" : ""}`} onClick={() => onChange(tab.value)}>
          {tab.label}{tab.count !== undefined && <span className="count">{tab.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function Drawer({ title, onClose, children, footer }: { title: ReactNode; onClose: () => void; children: ReactNode; footer?: ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <>
      <div className="overlay" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={typeof title === "string" ? title : undefined}>
        <div className="drawer-head"><h2>{title}</h2><button className="btn btn-ghost btn-icon" onClick={onClose} aria-label="Close"><X /></button></div>
        <div className="drawer-body">{children}</div>
        {footer && <div className="drawer-foot">{footer}</div>}
      </aside>
    </>
  );
}

export type Column<T> = { key: string; label: ReactNode; render: (row: T) => ReactNode; className?: string };

export function DataTable<T>({ rows, columns, rowKey, onRowClick, empty }: {
  rows: T[]; columns: Column<T>[]; rowKey: (row: T) => string | number; onRowClick?: (row: T) => void; empty?: ReactNode;
}) {
  if (rows.length === 0) return <>{empty ?? <EmptyState />}</>;
  return (
    <div className="table-wrap">
      <table className="table">
        <thead><tr>{columns.map((c) => <th key={c.key}>{c.label}</th>)}</tr></thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)} className={onRowClick ? "clickable" : undefined} onClick={onRowClick ? () => onRowClick(row) : undefined}>
              {columns.map((c) => <td key={c.key} className={c.className}>{c.render(row)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Pager({ count, page, hasNext, hasPrev, onPage, noun = "items" }: { count: number; page: number; hasNext: boolean; hasPrev: boolean; onPage: (p: number) => void; noun?: string }) {
  return (
    <div className="pager">
      <span>{count} {noun}</span>
      <div className="row">
        <button className="btn btn-secondary btn-sm" disabled={!hasPrev} onClick={() => onPage(page - 1)}>Previous</button>
        <button className="btn btn-secondary btn-sm" disabled={!hasNext} onClick={() => onPage(page + 1)}>Next</button>
      </div>
    </div>
  );
}

export function Avatar({ name }: { name: string | null | undefined }) {
  return <span className="avatar" aria-hidden>{initials(name)}</span>;
}

/** <dt>/<dd> pairs for a key/value object (custom fields, catalog answers). */
export function PropRows({ data }: { data: Record<string, unknown> }) {
  return (
    <>
      {Object.entries(data).map(([key, value]) => (
        <Fragment key={key}>
          <dt>{key.replaceAll("_", " ")}</dt>
          <dd>{typeof value === "boolean" ? (value ? "Yes" : "No") : String(value ?? "—")}</dd>
        </Fragment>
      ))}
    </>
  );
}
