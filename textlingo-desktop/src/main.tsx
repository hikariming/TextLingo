import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
import "./lib/i18n";
import { ThemeProvider } from "./components/theme-provider";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <ThemeProvider defaultThemeName="california" defaultThemeMode="system">
      <App />
    </ThemeProvider>
  </React.StrictMode>
);
