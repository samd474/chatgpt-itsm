import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import {
  confirmTwoFactor, disableTwoFactor, getTwoFactorStatus, replaceRecoveryCodes, startTwoFactorSetup, type TwoFactorSetup,
} from "../../api/auth";
import { apiErrorMessage } from "../../api/client";
import { useAuth } from "../../auth/context";
import { Badge, Card, ErrorState, Field, LoadingState, Notice, PageHeader } from "../../components/ui";

const STATUS_KEY = ["two-factor-status"];

/** A code input plus submit button; used for confirming setup, new recovery codes and turning 2FA off. */
function CodeForm({ label, submit, pending, error, onSubmit, tone = "primary" }: {
  label: string; submit: string; pending: boolean; error: unknown; onSubmit: (code: string) => void; tone?: "primary" | "danger";
}) {
  const [code, setCode] = useState("");
  const send = (e: FormEvent) => { e.preventDefault(); if (code.trim()) onSubmit(code.trim()); };
  return (
    <form className="stack" style={{ gap: 8 }} onSubmit={send} noValidate>
      <Field label={label}>
        <input className="input" autoComplete="one-time-code" value={code} onChange={(e) => setCode(e.target.value)} style={{ maxWidth: 220 }} />
      </Field>
      {error != null && <Notice tone="error">{apiErrorMessage(error)}</Notice>}
      <div><button className={`btn btn-${tone}`} disabled={pending || !code.trim()}>{submit}</button></div>
    </form>
  );
}

function RecoveryCodeList({ codes }: { codes: string[] }) {
  return (
    <div className="stack" style={{ gap: 8 }}>
      <Notice tone="warn">Save these recovery codes somewhere safe. Each works once if you lose your phone. They won't be shown again.</Notice>
      <ul aria-label="Recovery codes" style={{ fontFamily: "monospace", columns: 2, margin: 0 }}>
        {codes.map((c) => <li key={c}>{c}</li>)}
      </ul>
      <div><button type="button" className="btn btn-secondary" onClick={() => void navigator.clipboard?.writeText(codes.join("\n"))}>Copy codes</button></div>
    </div>
  );
}

export function SecurityPage() {
  const { user, refreshUser } = useAuth();
  const queryClient = useQueryClient();
  const status = useQuery({ queryKey: STATUS_KEY, queryFn: getTwoFactorStatus });
  const [setup, setSetup] = useState<TwoFactorSetup | null>(null);
  const [codes, setCodes] = useState<string[] | null>(null);
  const changed = async () => { await queryClient.invalidateQueries({ queryKey: STATUS_KEY }); await refreshUser(); };

  const start = useMutation({ mutationFn: startTwoFactorSetup, onSuccess: (s) => { setSetup(s); setCodes(null); } });
  const confirm = useMutation({ mutationFn: confirmTwoFactor, onSuccess: async (c) => { setSetup(null); setCodes(c); await changed(); } });
  const replace = useMutation({ mutationFn: replaceRecoveryCodes, onSuccess: async (c) => { setCodes(c); await changed(); } });
  const disable = useMutation({ mutationFn: disableTwoFactor, onSuccess: async () => { setCodes(null); await changed(); } });

  if (status.isLoading) return <LoadingState />;
  if (status.isError || !status.data) return <ErrorState message={apiErrorMessage(status.error)} />;
  const { enabled, required_by_role, recovery_codes_left } = status.data;

  return (
    <div className="stack">
      <PageHeader eyebrow="Your account" title="Sign-in security"
        description="Two-factor authentication asks for a code from an authenticator app after your password." />
      {user?.two_factor_setup_needed && (
        <Notice tone="warn">Your role requires two-factor authentication. Set it up to continue using the service desk.</Notice>
      )}
      <Card title="Two-factor authentication"
        actions={enabled ? <Badge tone="green" dot>On</Badge> : <Badge>Off</Badge>}>
        <div className="stack">
          {codes && <RecoveryCodeList codes={codes} />}

          {!enabled && !setup && (
            <div className="stack" style={{ gap: 8 }}>
              <p className="muted">You'll need an authenticator app such as Microsoft Authenticator, Google Authenticator or 1Password.</p>
              {start.isError && <Notice tone="error">{apiErrorMessage(start.error)}</Notice>}
              <div><button className="btn btn-primary" disabled={start.isPending} onClick={() => start.mutate()}>Set up authenticator app</button></div>
            </div>
          )}

          {!enabled && setup && (
            <div className="stack">
              <p>1. Scan this QR code with your authenticator app.</p>
              <img src={setup.qr_svg} alt="QR code for your authenticator app" width={200} height={200} style={{ background: "#fff" }} />
              <p className="subtle">Can't scan it? Enter this key instead: <code data-testid="totp-secret">{setup.secret}</code></p>
              <p>2. Enter the 6-digit code the app shows.</p>
              <CodeForm label="Code from the app" submit="Turn on" pending={confirm.isPending} error={confirm.error}
                onSubmit={(code) => confirm.mutate(code)} />
            </div>
          )}

          {enabled && (
            <>
              <p className="muted">
                {recovery_codes_left} recovery code{recovery_codes_left === 1 ? "" : "s"} left.
                {recovery_codes_left < 3 && " Make new ones soon."}
              </p>
              <h3>Make new recovery codes</h3>
              <p className="subtle">Your old recovery codes stop working.</p>
              <CodeForm label="Current code" submit="Make new codes" pending={replace.isPending} error={replace.error}
                onSubmit={(code) => replace.mutate(code)} />
              {required_by_role ? (
                <p className="subtle">Your role requires two-factor authentication, so it can't be turned off.</p>
              ) : (
                <>
                  <h3>Turn off</h3>
                  <CodeForm label="Current code or recovery code" submit="Turn off two-factor" tone="danger"
                    pending={disable.isPending} error={disable.error} onSubmit={(code) => disable.mutate(code)} />
                </>
              )}
            </>
          )}
        </div>
      </Card>
    </div>
  );
}
