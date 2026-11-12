import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import Register from "./pages/Register";
import Access from "./pages/Access";
import Scenario from "./pages/Scenario";

export default function App() {
  return (
    <div className="shell">
      <header>
        <h1>Дискреционная модель доступа</h1>
        <nav>
          <NavLink to="/register">Регистрация</NavLink>
          <NavLink to="/access">Мои ресурсы</NavLink>
          <NavLink to="/scenario">Сценарий-демонстрация</NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/register" replace />} />
          <Route path="/register" element={<Register />} />
          <Route path="/access" element={<Access />} />
          <Route path="/scenario" element={<Scenario />} />
        </Routes>
      </main>
    </div>
  );
}
