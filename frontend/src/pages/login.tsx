import { Link } from "react-router-dom";
import { ScanSearch } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/**
 * Login page shell. The form fields and real authentication are wired up in the
 * `feature/jwt-auth` PR — this establishes the route and layout.
 */
export function LoginPage() {
  return (
    <div className="flex min-h-svh items-center justify-center bg-background px-6 text-foreground">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <ScanSearch className="mx-auto size-6 text-primary" />
          <CardTitle className="mt-2">Welcome back</CardTitle>
          <CardDescription>Sign in to your CodeLens account</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button render={<Link to="/app" />} className="w-full">
            Continue to dashboard
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            Authentication arrives in the next milestone.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
