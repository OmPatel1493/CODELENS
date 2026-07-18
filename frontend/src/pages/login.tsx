import { AuthForm } from "@/components/auth-form";
import { useAuth } from "@/components/auth-provider";

export function LoginPage() {
  const { login } = useAuth();
  return <AuthForm mode="login" onSubmit={login} />;
}
