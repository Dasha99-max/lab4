import { FormEvent, useState } from "react";
import { api, errorText } from "../api";

export default function Register() {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    const r = await api("POST", "/register", { login, password });
    setBusy(false);
    if (r.ok) {
      setMsg({ ok: true, text: r.data.message === "user создан" ? "Пользователь создан. Теперь можно войти на странице «Мои ресурсы»." : r.data.message });
      setPassword("");
    } else {
      setMsg({ ok: false, text: `${errorText(r)} (код ${r.status})` });
    }
  }

  return (
    <section className="card narrow">
      <h2>Регистрация</h2>
      <form onSubmit={submit}>
        <label>
          Логин
          <input value={login} onChange={(e) => setLogin(e.target.value)} autoComplete="username" required />
          <small>3–32 символа: латинские буквы, цифры, точка, _ и -</small>
        </label>
        <label>
          Пароль
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" required />
          <small>Минимум 8 символов, заглавная и строчная буквы, цифра и спецсимвол</small>
        </label>
        <button disabled={busy}>{busy ? "Отправка…" : "Зарегистрироваться"}</button>
      </form>
      {msg && <p className={msg.ok ? "msg ok" : "msg err"} role="status">{msg.text}</p>}
    </section>
  );
}
