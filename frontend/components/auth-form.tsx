"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { toast } from "sonner";
import { login, register } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type AuthFormProps = {
  mode: "login" | "register";
};

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isLogin = mode === "login";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      if (isLogin) {
        await login(email, password);
        toast.success("Signed in.");
      } else {
        await register(email, password);
        toast.success("Account created.");
      }

      router.push("/");
      router.refresh();
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to continue right now.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="space-y-5" onSubmit={handleSubmit}>
      <div className="space-y-2">
        <label
          className="text-[11px] uppercase tracking-[0.22em] text-[var(--color-mist)]"
          htmlFor={`${mode}-email`}
        >
          Email
        </label>
        <Input
          id={`${mode}-email`}
          autoComplete="email"
          onChange={(event) => setEmail(event.target.value)}
          placeholder="you@example.com"
          type="email"
          value={email}
        />
      </div>

      <div className="space-y-2">
        <label
          className="text-[11px] uppercase tracking-[0.22em] text-[var(--color-mist)]"
          htmlFor={`${mode}-password`}
        >
          Password
        </label>
        <Input
          id={`${mode}-password`}
          autoComplete={isLogin ? "current-password" : "new-password"}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="At least 8 characters"
          type="password"
          value={password}
        />
      </div>

      {error ? (
        <div className="rounded-[1.15rem] border border-rose-400/25 bg-rose-400/10 p-4 text-sm text-[var(--color-paper)]">
          {error}
        </div>
      ) : null}

      <Button className="w-full" disabled={isSubmitting} type="submit">
        {isSubmitting
          ? isLogin
            ? "Signing in..."
            : "Creating account..."
          : isLogin
            ? "Sign in"
            : "Create account"}
      </Button>

      <p className="text-sm text-[var(--color-mist)]">
        {isLogin ? "Need an account?" : "Already have an account?"}{" "}
        <Link
          className="text-[var(--color-cyan)] underline-offset-4 hover:underline"
          href={isLogin ? "/register" : "/login"}
        >
          {isLogin ? "Create one" : "Sign in"}
        </Link>
      </p>
    </form>
  );
}
