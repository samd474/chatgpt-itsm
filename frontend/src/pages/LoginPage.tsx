import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import { apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/context";
import { homePath } from "../auth/roles";

const schema = z.object({
  username: z.string().min(1, "Username is required."),
  password: z.string().min(1, "Password is required."),
});

type LoginForm = z.infer<typeof schema>;

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [serverError, setServerError] = useState("");
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginForm>({
    resolver: zodResolver(schema),
  });

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
    <div className="login-page">
      <form className="login-card" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="eyebrow">ITSM</div>
        <h1>Sign in</h1>
        <p className="muted">Use your service desk account.</p>

        <label>Username
          <input autoComplete="username" {...register("username")} />
        </label>
        {errors.username && <div className="field-error">{errors.username.message}</div>}

        <label>Password
          <input type="password" autoComplete="current-password" {...register("password")} />
        </label>
        {errors.password && <div className="field-error">{errors.password.message}</div>}

        {serverError && <div className="alert alert--error">{serverError}</div>}
        <button className="button" disabled={isSubmitting}>
          {isSubmitting ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}
