"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ArrowRight, Lock, Mail, User } from "@/components/icons";

type Mode = "login" | "register";

export function AuthForm({ mode, nextPath }: { mode: Mode; nextPath: string }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const isRegister = mode === "register";

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      const response = await fetch(`/api/auth/${isRegister ? "register" : "login"}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(
          isRegister
            ? { email, password, display_name: displayName }
            : { email, password },
        ),
      });
      if (!response.ok) {
        let detail = "No se pudo completar la operación.";
        try {
          const payload = await response.json();
          if (typeof payload.detail === "string") detail = payload.detail;
          else if (Array.isArray(payload.detail)) detail = payload.detail[0]?.msg ?? detail;
        } catch {
          /* ignore */
        }
        throw new Error(detail);
      }
      router.push(nextPath);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado");
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="mt-8 space-y-4">
      {isRegister && (
        <div>
          <label className="label" htmlFor="display_name">
            Cómo te llamamos
          </label>
          <div className="relative">
            <User size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input
              id="display_name"
              name="display_name"
              type="text"
              autoComplete="name"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              className="field !pl-9"
              placeholder="Tu nombre"
              maxLength={120}
            />
          </div>
        </div>
      )}

      <div>
        <label className="label" htmlFor="email">
          Email
        </label>
        <div className="relative">
          <Mail size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="field !pl-9"
            placeholder="tu@email.com"
          />
        </div>
      </div>

      <div>
        <label className="label" htmlFor="password">
          Contraseña
        </label>
        <div className="relative">
          <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            id="password"
            name="password"
            type="password"
            autoComplete={isRegister ? "new-password" : "current-password"}
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="field !pl-9"
            placeholder={isRegister ? "Mínimo 8 caracteres" : "Tu contraseña"}
          />
        </div>
        {isRegister && (
          <p className="mt-1.5 text-[10px] text-muted">
            Guardamos un hash scrypt, nunca la contraseña en claro. Puedes borrar tu perfil y tus
            datos cuando quieras.
          </p>
        )}
      </div>

      {error && (
        <p className="border border-brick/30 bg-brick-soft px-3 py-2 text-[12px] text-brick" role="alert">
          {error}
        </p>
      )}

      <button type="submit" disabled={pending} className="btn btn-primary w-full !py-3.5">
        {pending ? "Procesando…" : isRegister ? "Crear cuenta" : "Entrar"}
        {!pending && <ArrowRight size={15} />}
      </button>

      <p className="text-center text-[12px] text-muted">
        {isRegister ? (
          <>
            ¿Ya tienes cuenta?{" "}
            <Link
              href={`/entrar${nextPath !== "/" ? `?next=${encodeURIComponent(nextPath)}` : ""}`}
              className="text-ink underline decoration-line-strong underline-offset-2 hover:text-signal-deep"
            >
              Entrar
            </Link>
          </>
        ) : (
          <>
            ¿Primera vez?{" "}
            <Link
              href={`/registro${nextPath !== "/" ? `?next=${encodeURIComponent(nextPath)}` : ""}`}
              className="text-ink underline decoration-line-strong underline-offset-2 hover:text-signal-deep"
            >
              Crear cuenta gratis
            </Link>
          </>
        )}
      </p>
    </form>
  );
}
