import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import { apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/context";
import { homePath } from "../auth/roles";
import { Field, Notice } from "../components/ui";

const schema = z.object({
  username: z.string().min(1, "Enter your username."),
  password: z.string().min(1, "Enter your password."),
});
type LoginForm = z.infer<typeof schema>;

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [serverError, setServerError] = useState("");
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginForm>({ resolver: zodResolver(schema) });

  if (user) return <Navigate to={homePath(user)} replace />;

  async function onSubmit(values: LoginForm) {
    setServerError("");
    try {
      const loggedIn = await login(values.username, values.password);
      const requested = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;
      navigate(requested || homePath(loggedIn), { replace: true });
    } catch (error) {
      setServerError(apiErrorMessage(error));
    }
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
