import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, errorText } from "../api";

interface Item {
  id: number;
  title: string;
  owner_login: string;
  is_owner: boolean;
  my_permissions: { read: boolean; update: boolean; delete: boolean };
}

const yn = (v: boolean) => (v ? "да" : "нет");

export default function Access() {
  const [token, setToken] = useState<string | null>(sessionStorage.getItem("token"));
  const [me, setMe] = useState<string | null>(sessionStorage.getItem("login"));
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [items, setItems] = useState<Item[]>([]);
  const [users, setUsers] = useState<string[]>([]);
  const [log, setLog] = useState<string[]>([]);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [grant, setGrant] = useState({ rid: "", login: "", read: true, update: false, delete: false });
  const [openId, setOpenId] = useState("");

  const note = (text: string) => setLog((l) => [text, ...l].slice(0, 12));

  const refresh = useCallback(async () => {
    if (!token) return;
    const [a, b] = await Promise.all([api("GET", "/resources", undefined, token), api("GET", "/users", undefined, token)]);
    if (a.status === 401) return logout();
    if (a.ok) setItems(a.data);
    if (b.ok) setUsers(b.data);
  }, [token]);

  useEffect(() => { refresh(); }, [refresh]);

  function logout() {
    sessionStorage.clear();
    setToken(null);
    setMe(null);
    setItems([]);
  }

  async function doLogin(e: FormEvent) {
    e.preventDefault();
    const r = await api("POST", "/login", { login, password });
    if (!r.ok) return note(`Вход: ${errorText(r)} (${r.status})`);
    sessionStorage.setItem("token", r.data.access_token);
    sessionStorage.setItem("login", r.data.login);
    setToken(r.data.access_token);
    setMe(r.data.login);
    setPassword("");
  }

  async function create(e: FormEvent) {
    e.preventDefault();
    const r = await api("POST", "/resources", { title, content }, token);
    note(r.ok ? `Создан ресурс #${r.data.id}` : `Создание: ${errorText(r)} (${r.status})`);
    if (r.ok) { setTitle(""); setContent(""); refresh(); }
  }

  async function act(kind: "read" | "update" | "delete", id: number | string) {
    let r;
    if (kind === "read") r = await api("GET", `/resources/${id}`, undefined, token);
    else if (kind === "update") {
      const t = window.prompt("Новое название:");
      if (!t) return;
      r = await api("PUT", `/resources/${id}`, { title: t, content: "изменено через UI" }, token);
    } else r = await api("DELETE", `/resources/${id}`, undefined, token);
    const label = { read: "Чтение", update: "Изменение", delete: "Удаление" }[kind];
    if (r.ok) note(`✔ ${label} #${id}: ${r.status}${kind === "read" ? ` — «${r.data.title}»: ${r.data.content}` : ""}`);
    else note(`✖ ${label} #${id}: ${r.status} — ${errorText(r)}`);
    refresh();
  }

  async function doGrant(e: FormEvent) {
    e.preventDefault();
    const r = await api("PUT", `/resources/${grant.rid}/permissions`, {
      login: grant.login, can_read: grant.read, can_update: grant.update, can_delete: grant.delete,
    }, token);
    note(r.ok ? `✔ Права для ${grant.login} на #${grant.rid} сохранены` : `✖ Выдача прав: ${r.status} — ${errorText(r)}`);
  }

  if (!token) {
    return (
      <section className="card narrow">
        <h2>Вход</h2>
        <form onSubmit={doLogin}>
          <label>Логин<input value={login} onChange={(e) => setLogin(e.target.value)} autoComplete="username" required /></label>
          <label>Пароль<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required /></label>
          <button>Войти</button>
        </form>
        {log[0] && <p className="msg err">{log[0]}</p>}
      </section>
    );
  }

  return (
    <>
      <section className="card">
        <div className="row between">
          <h2>Вы вошли как <code>{me}</code></h2>
          <button className="ghost" onClick={logout}>Выйти</button>
        </div>
        <table>
          <thead>
            <tr><th>ID</th><th>Название</th><th>Владелец</th><th>Читать</th><th>Изменять</th><th>Удалять</th><th>Действия</th></tr>
          </thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.id}>
                <td>{i.id}</td><td>{i.title}</td><td>{i.owner_login}{i.is_owner && " (вы)"}</td>
                <td>{yn(i.my_permissions.read)}</td><td>{yn(i.my_permissions.update)}</td><td>{yn(i.my_permissions.delete)}</td>
                <td className="actions">
                  <button className="ghost" onClick={() => act("read", i.id)}>Читать</button>
                  <button className="ghost" onClick={() => act("update", i.id)}>Изменить</button>
                  <button className="ghost danger" onClick={() => act("delete", i.id)}>Удалить</button>
                </td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={7} className="empty">Ресурсов пока нет. Создайте первый ниже.</td></tr>}
          </tbody>
        </table>
      </section>

      <div className="grid">
        <section className="card">
          <h3>Создать ресурс</h3>
          <form onSubmit={create}>
            <label>Название<input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={100} required /></label>
            <label>Содержимое<textarea value={content} onChange={(e) => setContent(e.target.value)} rows={3} /></label>
            <button>Создать</button>
          </form>
        </section>

        <section className="card">
          <h3>Выдать права (только владелец)</h3>
          <form onSubmit={doGrant}>
            <label>ID ресурса<input value={grant.rid} onChange={(e) => setGrant({ ...grant, rid: e.target.value })} inputMode="numeric" required /></label>
            <label>Пользователь
              <input list="users" value={grant.login} onChange={(e) => setGrant({ ...grant, login: e.target.value })} required />
              <datalist id="users">{users.filter((u) => u !== me).map((u) => <option key={u} value={u} />)}</datalist>
            </label>
            <div className="row">
              {(["read", "update", "delete"] as const).map((k) => (
                <label key={k} className="check">
                  <input type="checkbox" checked={grant[k]} onChange={(e) => setGrant({ ...grant, [k]: e.target.checked })} />
                  {{ read: "чтение", update: "изменение", delete: "удаление" }[k]}
                </label>
              ))}
            </div>
            <button>Сохранить права</button>
          </form>
        </section>

        <section className="card">
          <h3>Открыть ресурс по ID</h3>
          <p className="hint">Проверка отказа: попробуйте открыть чужой ресурс, на который у вас нет права.</p>
          <div className="row">
            <input value={openId} onChange={(e) => setOpenId(e.target.value)} inputMode="numeric" placeholder="ID" />
            <button onClick={() => openId && act("read", openId)}>Читать</button>
          </div>
        </section>
      </div>

      <section className="card">
        <h3>Результаты запросов</h3>
        <ul className="log">
          {log.map((l, i) => <li key={i} className={l.startsWith("✖") ? "err" : l.startsWith("✔") ? "ok" : ""}>{l}</li>)}
          {log.length === 0 && <li className="empty">Здесь появятся ответы backend.</li>}
        </ul>
      </section>
    </>
  );
}
