import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppRoutes } from '@/routes'
import { refreshAuthSession } from '@/lib/api-client'
import { authStore } from '@/stores/authStore'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30000 },
  },
})

async function bootstrap() {
  try {
    await refreshAuthSession()
  } catch {
    authStore.getState().logout()
  }

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <AppRoutes />
      </QueryClientProvider>
    </StrictMode>,
  )
}

void bootstrap()
