import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import "./index.css";
import "./assets/Styles/Primitives.css";
import "./assets/Styles/Tokens.css";
import "./assets/Styles/Interaction.css";
import App from "./App.tsx";

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
