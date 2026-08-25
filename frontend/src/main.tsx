import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { AuthProvider } from "./auth/AuthContext";
import { RouterProvider } from "./routes/router";
import { ThemeProvider } from "./theme/ThemeContext";
createRoot(document.getElementById("root")!).render(<StrictMode><ThemeProvider><RouterProvider><AuthProvider><App/></AuthProvider></RouterProvider></ThemeProvider></StrictMode>);
