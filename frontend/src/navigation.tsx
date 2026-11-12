import {
  Link as RouterLink,
  NavLink as RouterNavLink,
  useNavigate as useRouterNavigate,
} from 'react-router-dom'
import type { LinkProps, NavigateOptions, NavLinkProps, To } from 'react-router-dom'

function canAnimateNavigation() {
  return typeof document.startViewTransition === 'function' &&
    !window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function Link(props: LinkProps) {
  return <RouterLink viewTransition={canAnimateNavigation()} {...props} />
}

export function NavLink(props: NavLinkProps) {
  return <RouterNavLink viewTransition={canAnimateNavigation()} {...props} />
}

export function useNavigate() {
  const navigate = useRouterNavigate()
  return (to: To, options?: NavigateOptions) => navigate(to, { viewTransition: canAnimateNavigation(), ...options })
}
