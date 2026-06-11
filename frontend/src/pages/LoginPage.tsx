import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type LoginPageProps = {
  errorMessage?: string;
  onLogin: (payload: { username: string; password: string }) => Promise<void>;
};

export function LoginPage({ errorMessage, onLogin }: LoginPageProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    try {
      await onLogin({ username, password });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-dvh place-items-center p-4">
      <Card className="w-[min(92vw,25rem)]">
        <CardHeader>
          <img className="rounded-md" src="/static/img/logo.webp" alt="鲸落" width="48" height="48" />
          <span className="font-mono text-xs tracking-[0.06em] text-muted-foreground uppercase">React console</span>
          <CardTitle className="text-2xl">鲸落控制台</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-3" onSubmit={handleSubmit}>
            <label className="grid gap-1.5 text-sm text-muted-foreground">
              <span>用户名</span>
              <Input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} />
            </label>
            <label className="grid gap-1.5 text-sm text-muted-foreground">
              <span>密码</span>
              <Input
                autoComplete="current-password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            {errorMessage ? <p className="text-sm text-destructive">{errorMessage}</p> : null}
            <Button disabled={isSubmitting} type="submit">
              {isSubmitting ? "登录中" : "登录"}
            </Button>
            <a className="text-center text-sm text-muted-foreground underline-offset-4 hover:underline" href="/auth/login">
              使用旧版登录页
            </a>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
