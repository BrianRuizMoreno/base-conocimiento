---
name: react-frontend
description: React 18 + Vite + TypeScript + Tailwind CSS frontend for the RAG admin panel and chat. Uses pnpm exclusively. Supports dark mode, tabbed admin dashboard, real-time metrics charts.
---

# React Frontend Patterns

## Project Structure
```
frontend/src/
├── main.tsx                    # React root + StrictMode
├── App.tsx                     # Router + providers
├── index.css                   # Tailwind directives + dark mode variables
├── pages/
│   ├── Dashboard.tsx           # Admin landing: metric cards
│   ├── Collection.tsx          # Upload zone + doc list + delete
│   ├── Chat.tsx                # Chat RAG with image inline
│   ├── Analysis.tsx            # Summary + predictive + compare
│   ├── admin/
│   │   ├── AdminDashboard.tsx  # Tabs container for admin panel
│   │   ├── TokenUsage.tsx      # Token/cost charts
│   │   ├── ServerStatus.tsx    # Disk, RAM, CPU bars
│   │   ├── ErrorLog.tsx        # Error table with filters
│   │   ├── ExecutionLog.tsx    # Operation log table
│   │   ├── Settings.tsx        # API keys + model config tabs
│   │   └── CollectionsAdmin.tsx# Manage collections + future users
│   └── Docs.tsx                # Embedded markdown docs
├── components/
│   ├── admin/
│   │   ├── MetricCard.tsx
│   │   ├── TimeFilter.tsx      # 24h/7d/30d/all selector
│   │   ├── TokenChart.tsx      # Recharts line chart
│   │   ├── CostChart.tsx
│   │   ├── DiskUsageBar.tsx
│   │   ├── LogTable.tsx
│   │   └── DarkModeToggle.tsx  # Sun/moon icon
│   ├── upload/
│   │   └── DropZone.tsx        # Drag & drop + progress
│   ├── chat/
│   │   ├── ChatWindow.tsx
│   │   ├── MessageBubble.tsx   # Text + images + sources
│   │   └── ImagenInline.tsx    # Render image from related_media
│   ├── graph/
│   │   └── GrafoEntidades.tsx  # D3/Cytoscape.js entity graph
│   └── layout/
│       ├── Sidebar.tsx         # Navigation links
│       └── Header.tsx          # Logo + dark toggle + user
├── hooks/
│   └── useApi.ts               # React Query wrappers
├── lib/
│   ├── client.ts               # Axios/Fetch client for FastAPI
│   └── utils.ts
└── context/
    ├── ThemeContext.tsx          # Dark mode state + localStorage
    └── AuthContext.tsx           # PIN auth state
```

## Conventions
- Use pnpm exclusively. No npm.
- Functional components + hooks
- Props typed with interfaces
- React Query for server state caching
- Tailwind `dark:` variant for dark mode
- `className` utility: `clsx` + `tailwind-merge` → `cn()` helper
- Icons: `lucide-react`

## Dark Mode
```tsx
// tailwind.config.ts
darkMode: 'class'

// ThemeContext.tsx
toggleDark = () => {
  document.documentElement.classList.toggle('dark');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
}
```

## API Client
```ts
const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  headers: { 'Content-Type': 'application/json' }
});

// Add PIN header after auth
client.interceptors.request.use(config => {
  const pin = localStorage.getItem('pin');
  if (pin) config.headers['X-Auth-PIN'] = pin;
  return config;
});
```

## Admin Tabs Pattern
```tsx
// AdminDashboard.tsx
const [activeTab, setActiveTab] = useState<'dashboard'|'tokens'|'server'|'errors'|'executions'|'settings'>('dashboard');

const tabs = [
  { id: 'dashboard', label: '📊 Dashboard', component: <DashboardContent /> },
  { id: 'tokens', label: '🪙 Tokens', component: <TokenUsage /> },
  // ...
];

return (
  <div>
    <div className="flex gap-2 border-b">
      {tabs.map(t => (
        <button key={t.id} onClick={() => setActiveTab(t.id)} className={cn("px-4 py-2", activeTab===t.id && "border-b-2 border-blue-500")}>
          {t.label}
        </button>
      ))}
    </div>
    <div className="p-4">{tabs.find(t => t.id === activeTab)?.component}</div>
  </div>
);
```
