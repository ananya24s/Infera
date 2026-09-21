import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import StatusBar from "./components/StatusBar";
import About from "./pages/About";
import Home from "./pages/Home";
import HowItWorks from "./pages/HowItWorks";
import Research from "./pages/Research";
import "./App.css";

const NAV = [
  { to: "/", label: "home", end: true },
  { to: "/research", label: "research" },
  { to: "/how-it-works", label: "how-it-works" },
  { to: "/about", label: "about" },
];

export default function App() {
  const { pathname } = useLocation();
  const cwd = pathname === "/" ? "~" : `~${pathname}`;

  return (
    <div className="app">
      <div className="term-chrome">
        <span className="term-dot term-dot-r" />
        <span className="term-dot term-dot-y" />
        <span className="term-dot term-dot-g" />
        <span className="term-chrome-title">guest@infera: {cwd}</span>
      </div>

      <header className="site-header">
        <NavLink to="/" className="brand-link">
          <span className="brand-mark">
            infera<span className="brand-cursor" />
          </span>
        </NavLink>
        <nav className="site-nav">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => (isActive ? "active" : "")}>
              {n.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="site-main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/research" element={<Research />} />
          <Route path="/how-it-works" element={<HowItWorks />} />
          <Route path="/about" element={<About />} />
          <Route path="*" element={<Home />} />
        </Routes>
      </main>

      <StatusBar />
    </div>
  );
}
