import {
  Link as RouterLink,
  NavLink as RouterNavLink,
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

function useLinkTransition(to: To, relative?: LinkProps['relative']) {
  const enabled = useViewTransitions()
  const current = useLocation()
  const destination = useResolvedPath(to, { relative })
  return enabled && destination.pathname.replace(/\/$/, '') !== current.pathname.replace(/\/$/, '')
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
  const viewTransition = useViewTransitions()
  return (to: To, options?: NavigateOptions) => navigate(to, {
    ...options, viewTransition: viewTransition && options?.viewTransition !== false,
  })
}
