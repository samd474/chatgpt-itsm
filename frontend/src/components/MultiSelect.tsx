import { Check, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Option } from "./form";

/** Chips + searchable dropdown; replaces the native <select multiple>. */
export function MultiSelect({ options, value, onChange, disabled, placeholder = "Add…" }: {
  options: Option[]; value: (string | number)[]; onChange: (v: (string | number)[]) => void; disabled?: boolean; placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const selected = new Set(value.map(String));
  const filtered = useMemo(
    () => options.filter((o) => o.label.toLowerCase().includes(query.toLowerCase())).slice(0, 100),
    [options, query],
  );

  useEffect(() => {
    const onClick = (e: MouseEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const toggle = (o: Option) => {
    onChange(selected.has(String(o.value)) ? value.filter((v) => String(v) !== String(o.value)) : [...value, o.value]);
    setQuery("");
    input.current?.focus();
  };
  const labelOf = (v: string | number) => options.find((o) => String(o.value) === String(v))?.label ?? String(v);

  return (
    <div className="multi" ref={root}>
      <div className="multi-box" onClick={() => { if (!disabled) { setOpen(true); input.current?.focus(); } }}>
        {value.map((v) => (
          <span className="chip" key={String(v)}>{labelOf(v)}
            {!disabled && <button type="button" aria-label={`Remove ${labelOf(v)}`} onClick={(e) => { e.stopPropagation(); onChange(value.filter((x) => x !== v)); }}><X /></button>}
          </span>
        ))}
        {!disabled && (
          <input ref={input} value={query} placeholder={value.length ? "" : placeholder} aria-label={placeholder}
            onFocus={() => setOpen(true)}
            onChange={(e) => { setQuery(e.target.value); setActive(0); setOpen(true); }}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, filtered.length - 1)); }
              else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
              else if (e.key === "Enter" && filtered[active]) { e.preventDefault(); toggle(filtered[active]); }
              else if (e.key === "Backspace" && !query && value.length) onChange(value.slice(0, -1));
              else if (e.key === "Escape") setOpen(false);
            }} />
        )}
      </div>
      {open && !disabled && (
        <div className="popover" role="listbox">
          {filtered.length === 0 && <div className="option subtle">No matches</div>}
          {filtered.map((o, i) => (
            <button type="button" key={String(o.value)} role="option" aria-selected={selected.has(String(o.value))}
              className={`option${i === active ? " active" : ""}`} onMouseEnter={() => setActive(i)} onClick={() => toggle(o)}>
              <span className="check">{selected.has(String(o.value)) && <Check />}</span>{o.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
