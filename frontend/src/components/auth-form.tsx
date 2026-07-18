/**
 * Shared email/password form for login and register. The parent supplies the
 * submit action (login vs register); this component owns field state, inline
 * error display, and the pending state.
 */

import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ScanSearch } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";

interface AuthFormProps {
  mode: "login" | "register";
  onSubmit: (email: string, password: string) => Promise<void>;
}

const COPY = {
  login: {
    title: "Welcome back",
    description: "Sign in to your CodeLens account",
    action: "Sign in",
    altText: "Need an account?",
    altLink: "/register",
    altLabel: "Create one",
  },
  register: {
    title: "Create your account",
    description: "Start indexing and searching your code",
    action: "Create account",
    altText: "Already have an account?",
    altLink: "/login",
    altLabel: "Sign in",
  },
} as const;

export function AuthForm({ mode, onSubmit }: AuthFormProps) {
  const copy = COPY[mode];
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      await onSubmit(email, password);
      // Return to the page the user was headed to, or the dashboard.
      const from = (location.state as { from?: { pathname: string } })?.from;
      navigate(from?.pathname ?? "/app", { replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Something went wrong. Try again.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex min-h-svh items-center justify-center bg-background px-6 text-foreground">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <ScanSearch className="mx-auto size-6 text-primary" />
          <CardTitle className="mt-2">{copy.title}</CardTitle>
          <CardDescription>{copy.description}</CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete={
                  mode === "login" ? "current-password" : "new-password"
                }
                required
                minLength={mode === "register" ? 8 : undefined}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}
          </CardContent>
          <CardFooter className="mt-4 flex-col gap-3">
            <Button type="submit" className="w-full" disabled={pending}>
              {pending ? "Please wait…" : copy.action}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              {copy.altText}{" "}
              <Link to={copy.altLink} className="text-foreground underline">
                {copy.altLabel}
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
