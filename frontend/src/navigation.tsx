import {
  Link as RouterLink,
  NavLink as RouterNavLink,
  resolvePath,
  useLocation,
  useNavigate as useRouterNavigate,
  useResolvedPath,
  useViewTransitionState,
} from 'react-router-dom'
import type { CSSProperties } from 'react'
import type { LinkProps, NavigateOptions, NavLinkProps, To } from 'react-router-dom'
import { useMotionSettings } from './motion-settings'

function useViewTransitions() {
  const { enabled } = useMotionSettings()
  return enabled && typeof document.startViewTransition === 'function'
}

function changesPage(current: string, destination: string) {
  return current.replace(/\/$/, '') !== destination.replace(/\/$/, '')
}

function useLinkTransition(to: To, relative?: LinkProps['relative']) {
  const enabled = useViewTransitions()
  const { pathname } = useLocation()
  const destination = useResolvedPath(to, { relative })
  return enabled && changesPage(pathname, destination.pathname)
}

export function Link({ viewTransition = true, ...props }: LinkProps) {
  const enabled = useLinkTransition(props.to, props.relative)
  return <RouterLink {...props} viewTransition={enabled && viewTransition} />
}

export function NavLink({ viewTransition = true, ...props }: NavLinkProps) {
  const enabled = useLinkTransition(props.to, props.relative)
  return <RouterNavLink {...props} viewTransition={enabled && viewTransition} />
}

export function useSharedArt(to: To, name: string, key?: string): CSSProperties | undefined {
  const enabled = useViewTransitions()
  const transitioning = useViewTransitionState(to)
  const suffix = key && Array.from(key, character => character.codePointAt(0)!.toString(36)).join('-')
  return enabled && transitioning ? { viewTransitionName: suffix ? name + '-' + suffix : name } : undefined
}

export function useNavigate() {
  const navigate = useRouterNavigate()
  const { pathname } = useLocation()
  const enabled = useViewTransitions()
  return (to: To, options?: NavigateOptions) => navigate(to, {
    ...options,
    viewTransition: enabled && options?.viewTransition !== false && changesPage(pathname, resolvePath(to, pathname).pathname),
  })
}
