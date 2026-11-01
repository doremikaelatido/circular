import { useState, type FormEvent } from "react";
import { CalendarDays } from "lucide-react";
import { useAuth } from "../features/auth/AuthContext";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";

export function AuthPage() {
  const { login, register, busy, error } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nickname, setNickname] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    try {
      if (mode === "register") await register(email, password, nickname);
      else await login(email, password);
    } catch {
      setFormError(error ?? "Please check your details and try again.");
    }
  }

  return (
    <main className="auth-page">
      <div className="auth-card">
        <div className="brand-mark"><CalendarDays /><span>Circle</span></div>
        <h1>{mode === "login" ? "Welcome back" : "Find your people, make a plan"}</h1>
        <p>Discover what's happening with your circle.</p>
        <form className="form-stack" onSubmit={submit}>
          {mode === "register" && <label>Nickname<Input required maxLength={40} value={nickname} onChange={(e) => setNickname(e.target.value)} /></label>}
          <label>Email<Input required type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
          <label>Password<Input required minLength={10} type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(e) => setPassword(e.target.value)} /></label>
          {(formError || error) && <div className="error-banner" role="alert">{formError || error}</div>}
          <Button className="button button-primary full-width" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Log in" : "Create account"}</Button>
        </form>
        <button className="text-button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setFormError(null); }}>
          {mode === "login" ? "New to Circle? Create an account" : "Already have an account? Log in"}
        </button>
      </div>
    </main>
  );
}
