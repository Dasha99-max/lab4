import { useState } from "react";
import { api, ApiResult } from "../api";

interface Step {
  title: string;
  expect: number;
  got?: number;
  detail?: string;
}

const PASSWORD = "Demo!Pass123";

export default function Scenario() {
  const [steps, setSteps] = useState<Step[]>([]);
  const [running, setRunning] = useState(false);

  async function run() {
    setRunning(true);
    const out: Step[] = [];
    const push = () => setSteps([...out]);
    const check = async (title: string, expect: number, call: () => Promise<ApiResult>) => {
      const r = await call();
      const d = r.data && typeof r.data.detail === "string" ? r.data.detail : r.data?.title ? `«${r.data.title}»` : "";
      out.push({ title, expect, got: r.status, detail: d });
      push();
      return r;
    };

    const s = Math.random().toString(36).slice(2, 7);
    const names = { a: `alice_${s}`, b: `bob_${s}`, c: `carol_${s}` };
    const tok: Record<string, string> = {};

    for (const [k, name] of Object.entries(names))
      await check(`Регистрация ${name}`, 201, () => api("POST", "/register", { login: name, password: PASSWORD }));
    for (const [k, name] of Object.entries(names)) {
      const r = await api("POST", "/login", { login: name, password: PASSWORD });
      tok[k] = r.data?.access_token ?? "";
    }

    const created = await check("alice создаёт ресурс (она владелец)", 201, () =>
      api("POST", "/resources", { title: "Отчёт alice", content: "конфиденциально" }, tok.a));
    const id = created.data?.id;

    await check("bob читает ресурс alice — права ещё нет", 403, () => api("GET", `/resources/${id}`, undefined, tok.b));
    await check("bob пытается выдать СЕБЕ право (он не владелец)", 403, () =>
      api("PUT", `/resources/${id}/permissions`, { login: names.b, can_read: true, can_update: true, can_delete: true }, tok.b));
    await check("alice выдаёт bob право на чтение", 200, () =>
      api("PUT", `/resources/${id}/permissions`, { login: names.b, can_read: true }, tok.a));
    await check("bob читает ресурс — право есть", 200, () => api("GET", `/resources/${id}`, undefined, tok.b));
    await check("bob изменяет ресурс — права на изменение нет", 403, () =>
      api("PUT", `/resources/${id}`, { title: "взлом", content: "" }, tok.b));
    await check("carol читает ресурс — права не выдавали", 403, () => api("GET", `/resources/${id}`, undefined, tok.c));
    await check("alice выдаёт bob право на изменение", 200, () =>
      api("PUT", `/resources/${id}/permissions`, { login: names.b, can_read: true, can_update: true }, tok.a));
    await check("bob изменяет ресурс — теперь можно", 200, () =>
      api("PUT", `/resources/${id}`, { title: "Отчёт (правка bob)", content: "обновлено" }, tok.b));
    await check("bob удаляет ресурс — права на удаление нет", 403, () => api("DELETE", `/resources/${id}`, undefined, tok.b));
    await check("alice отзывает все права bob", 200, () =>
      api("PUT", `/resources/${id}/permissions`, { login: names.b }, tok.a));
    await check("bob читает ресурс после отзыва", 403, () => api("GET", `/resources/${id}`, undefined, tok.b));
    await check("alice удаляет свой ресурс", 204, () => api("DELETE", `/resources/${id}`, undefined, tok.a));

    setRunning(false);
  }

  const passed = steps.filter((s) => s.got === s.expect).length;

  return (
    <section className="card">
      <h2>Сценарий: владелец выдаёт право, получатель получает доступ, остальные — отказ</h2>
      <p className="hint">Кнопка создаёт трёх новых пользователей и выполняет цепочку запросов к backend. Каждое решение принимает сервер.</p>
      <button onClick={run} disabled={running}>{running ? "Выполняется…" : "Запустить сценарий"}</button>
      {steps.length > 0 && (
        <>
          <p className="summary">Совпало с ожиданием: {passed} из {steps.length}</p>
          <table>
            <thead><tr><th>Шаг</th><th>Ожидали</th><th>Получили</th><th>Ответ сервера</th></tr></thead>
            <tbody>
              {steps.map((s, i) => (
                <tr key={i} className={s.got === s.expect ? "okrow" : "errrow"}>
                  <td>{s.title}</td><td>{s.expect}</td><td>{s.got}</td><td>{s.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}
