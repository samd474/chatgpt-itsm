import { zodResolver } from "@hookform/resolvers/zod";
import { useState, type FormEvent } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import { apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/context";
import { homePath } from "../auth/roles";
import { Field, Notice } from "../components/ui";
import type { User } from "../types";

const schema = z.object({
  username: z.string().min(1, "Enter your username."),
  password: z.string().min(1, "Enter your password."),
});
type LoginForm = z.infer<typeof schema>;

export function LoginPage() {
  const { user, login, verifyTwoFactor } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [serverError, setServerError] = useState("");
  const [needsCode, setNeedsCode] = useState(false);
  const [code, setCode] = useState("");
  const [verifying, setVerifying] = useState(false);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginForm>({ resolver: zodResolver(schema) });

  if (user) return <Navigate to={homePath(user)} replace />;

  function goOn(loggedIn: User) {
    const requested = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;
    navigate(loggedIn.two_factor_setup_needed ? "/account/security" : requested || homePath(loggedIn), { replace: true });
  }

  async function onSubmit(values: LoginForm) {
    setServerError("");
    try {
      const result = await login(values.username, values.password);
      if (result === "two_factor") setNeedsCode(true);
      else goOn(result);
    } catch (error) {
      setServerError(apiErrorMessage(error));
    }
  }

  async function onVerify(event: FormEvent) {
    event.preventDefault();
    if (!code.trim()) { setServerError("Enter the code from your authenticator app."); return; }
    setServerError("");
    setVerifying(true);
    try {
      goOn(await verifyTwoFactor(code));
    } catch (error) {
      setServerError(apiErrorMessage(error));
      setVerifying(false);
    }
  }

  if (needsCode) {
    return (
      <div className="auth">
        <div className="auth-card">
          <div className="brand"><span className="brand-mark">IT</span>Service Desk</div>
          <form onSubmit={onVerify} noValidate>
            <h1>Enter your sign-in code</h1>
            <p className="muted">Open your authenticator app and enter the 6-digit code. Lost your phone? Use one of your recovery codes.</p>
            <Field label="Code">
              <input className="input" autoComplete="one-time-code" inputMode="text" autoFocus value={code}
                onChange={(e) => setCode(e.target.value)} />
            </Field>
            {serverError && <Notice tone="error">{serverError}</Notice>}
            <button className="btn btn-primary" disabled={verifying}>{verifying ? "Checking…" : "Verify"}</button>
            <button type="button" className="btn btn-ghost" onClick={() => { setNeedsCode(false); setCode(""); setServerError(""); }}>
              Back
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="auth">
      <div className="auth-card">
        <div className="brand"><span className="brand-mark">IT</span>Service Desk</div>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <h1>Sign in to your account</h1>
          <Field label="Username" error={errors.username?.message}>
            <input className="input" autoComplete="username" autoFocus {...register("username")} />
          </Field>
          <Field label="Password" error={errors.password?.message}>
            <input className="input" type="password" autoComplete="current-password" {...register("password")} />
          </Field>
          {serverError && <Notice tone="error">{serverError}</Notice>}
          <button className="btn btn-primary" disabled={isSubmitting}>{isSubmitting ? "Signing in…" : "Sign in"}</button>
        </form>
        <p className="subtle" style={{ textAlign: "center" }}>Trouble signing in? Contact the service desk.</p>
      </div>
    </div>
  );
}
