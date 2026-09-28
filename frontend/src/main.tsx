import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '@design/tokens.css';
import './styles/app.css';
import { App } from './App';
import { StoreProvider } from './state/store';
import { parseHash } from './lib/route';

const route = parseHash(window.location.hash);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <StoreProvider
      initial={
        !route
          ? undefined
          : route.view === 'documents'
            ? { view: 'documents', docId: route.id ?? null, docTarget: route.paragraph ? { paragraph: route.paragraph, finding: route.finding } : null }
            : { view: route.view, selectedId: route.id ?? null }
      }
    >
      <App />
    </StoreProvider>
  </StrictMode>,
);
