import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { useLoaderData, useRevalidator } from 'react-router-dom'
import type { LoaderFunctionArgs } from 'react-router-dom'
import { api } from './api'
import type { User } from './api'

type SessionState = {
  user: User | null | undefined
  setUser: (user: User | null) => void
  error: unknown
  refresh: () => void
}

const SessionContext = createContext<SessionState | null>(null)

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>()
  const [error, setError] = useState<unknown>(null)
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    api<{ user: User | null }>('session/', { signal: controller.signal })
      .then(session => { setUser(session.user); setError(null) })
      .catch(error => { if (!controller.signal.aborted) setError(error) })
    return () => controller.abort()
  }, [revision])
  return <SessionContext.Provider value={{
    user, setUser, error, refresh: () => setRevision(value => value + 1),
  }}>{children}</SessionContext.Provider>
}

export function useSession() {
  const session = useContext(SessionContext)
  if (!session) throw new Error('SessionProvider is missing')
  return session
}

export function loadResource(path: string | ((args: LoaderFunctionArgs) => string)) {
  return async (args: LoaderFunctionArgs) => {
    try {
      return { data: await api(typeof path === 'string' ? path : path(args), { signal: args.request.signal }) }
    } catch (error) {
      return { error }
    }
  }
}

export function useResource<T>() {
  const resource = useLoaderData() as { data?: T; error?: unknown }
  const { revalidate } = useRevalidator()
  return {
    ...resource,
    retry: revalidate,
  }
}
