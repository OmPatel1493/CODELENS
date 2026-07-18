import { AuthForm } from "@/components/auth-form";
import { useAuth } from "@/components/auth-provider";

export function RegisterPage() {
  const { register } = useAuth();
  return <AuthForm mode="register" onSubmit={register} />;
}
