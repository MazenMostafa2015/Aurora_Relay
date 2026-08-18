import { type FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogTitle,
} from "@/components/ui/dialog";

interface ManusDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onLogin: (username: string, password: string) => Promise<boolean>;
  onRegister: (username: string, email: string, password: string) => Promise<boolean>;
  isSubmitting?: boolean;
  error?: string | null;
}

export function ManusDialog({
  open,
  onLogin,
  onRegister,
  onOpenChange,
  isSubmitting = false,
  error,
}: ManusDialogProps) {
  const [mode, setMode] = useState<"sign-in" | "register">("sign-in");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    if (!open) {
      setPassword("");
      setMode("sign-in");
    }
  }, [open]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (mode === "register") await onRegister(username.trim(), email.trim(), password);
    else await onLogin(username.trim(), password);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[min(92vw,420px)] bg-[#11191d] text-[#e8f0ee] border border-[#2a3c41] p-0 gap-0">
        <form onSubmit={handleSubmit}>
          <div className="flex flex-col gap-2 p-6 pb-3">
            <DialogTitle className="text-xl font-semibold">{mode === "sign-in" ? "Sign in to Aurora Relay" : "Create a local workspace account"}</DialogTitle>
            <DialogDescription className="text-sm text-[#9bb0b3]">Your credential and session stay on this local Aurora Relay service.</DialogDescription>
          </div>
          <div className="px-6 py-3 grid gap-4">
            <div className="grid gap-2"><Label htmlFor="aurora-username">Username</Label><Input id="aurora-username" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required disabled={isSubmitting} /></div>
            {mode === "register" && <div className="grid gap-2"><Label htmlFor="aurora-email">Email</Label><Input id="aurora-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required disabled={isSubmitting} /></div>}
            <div className="grid gap-2"><Label htmlFor="aurora-password">Password</Label><Input id="aurora-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={mode === "sign-in" ? "current-password" : "new-password"} minLength={mode === "register" ? 8 : 1} required disabled={isSubmitting} /></div>
            {error && <p className="text-sm text-[#f4b98f]" role="alert">{error}</p>}
          </div>
          <DialogFooter className="px-6 pt-2 pb-6 flex-col sm:flex-row gap-3">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting} className="border-[#2a3c41] text-[#c9d6d5]">Cancel</Button>
            <Button type="button" variant="ghost" onClick={() => setMode((current) => current === "sign-in" ? "register" : "sign-in")} disabled={isSubmitting} className="text-[#9bb0b3]">{mode === "sign-in" ? "Create account" : "Use existing account"}</Button>
            <Button type="submit" disabled={isSubmitting} className="bg-[#0b6b72] hover:bg-[#0d7b83] text-white">{isSubmitting ? "Working…" : mode === "sign-in" ? "Sign in" : "Create account"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
