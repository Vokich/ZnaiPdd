import { StrictMode, useEffect, useRef, useState } from 'react'
import type { ReactNode, RefObject } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, Navigate, Outlet, RouterProvider, ScrollRestoration, useLocation, useNavigation, useNavigationType, useViewTransitionState } from 'react-router-dom'
import '@fontsource-variable/golos-text'
import './styles.css'
import './landing-motion.css'
import { loadResource, SessionProvider, useSession } from './state'
import type { Role } from './api'
import { ButtonLink, Footer, Header, Loading, LoadError, PortalHeading } from './ui'
import { HomePage, LoginPage, RegisterPage } from './public-pages'
import { AccountPage, EditProfilePage, PasswordPage, TeacherPage } from './account-pages'
import { QuizPage, QuizzesPage, ResultPage, quizInfo } from './quiz-pages'
import { SignDetailPage, SignsHomePage, SignsListPage, SignTestPage } from './sign-pages'
import { useViewportMotion } from './viewport-motion'
import privacyText from './privacy.html?raw'

function Gate({ children, role }: { children: ReactNode; role?: Role }) {
  const { user, error, refresh } = useSession()
  const location = useLocation()
  if (error && user === undefined) return <LoadError error={error} retry={refresh} />
  if (user === undefined) return <Loading />
  if (!user) return <Navigate to="/login/" state={{ next: location.pathname + location.search }} replace />
  if (role && user.role !== role) return <div className="panel status-panel"><h1>Раздел недоступен</h1><ButtonLink to="/profile/">В мой кабинет →</ButtonLink></div>
  return children
}

function PrivacyPage() {
  return <>
    <PortalHeading title="Согласие на обработку персональных данных">Региональный проект «Знай ПДД»</PortalHeading>
    <article className="panel policy">
      <div data-scroll-copy="" dangerouslySetInnerHTML={{ __html: privacyText }} />
      <div className="actions" data-scroll-reveal="quiet"><ButtonLink to="/reg/" light>← К регистрации</ButtonLink></div>
    </article>
  </>
}

function NotFoundPage() {
  return <div className="panel status-panel"><h1>Страница не найдена</h1><ButtonLink to="/">На главную →</ButtonLink></div>
}

function Page({ pathname, portal, pending, main }: { pathname: string; portal: boolean; pending: boolean; main: RefObject<HTMLElement | null> }) {
  const transitioning = useViewTransitionState(pathname)
  // Keep the chosen entrance for this mount after the browser snapshot has gone away.
  const [nativeEntrance] = useState(transitioning)
  return <main id="main" ref={main} tabIndex={-1} className={portal ? 'page-motion portal' : 'page-motion'} aria-busy={pending || undefined} data-native-motion={nativeEntrance ? '' : undefined}>
    <Outlet />
  </main>
}

function App() {
  const { pathname } = useLocation()
  const navigation = useNavigationType()
  const pending = useNavigation().state !== 'idle'
  const site = useRef<HTMLDivElement>(null)
  const main = useRef<HTMLElement>(null)
  const previousPath = useRef(pathname)
  const home = pathname === '/'
  const auth = /^\/(login|reg)\/?$/.test(pathname)
  const kind = home ? 'home' : auth ? 'auth' : 'portal'
  useViewportMotion(site, pathname)

  useEffect(() => {
    const changed = previousPath.current !== pathname
    previousPath.current = pathname
    if (changed && navigation !== 'POP') main.current?.focus({ preventScroll: true })
    const title = main.current?.querySelector('h1')?.textContent
    document.title = title && !home ? title + ' — Знай ПДД' : 'Знай ПДД'
  }, [pathname, home, navigation])

  return <div ref={site} className={`site site-${kind}`}>
    <a className="skip-link" href="#main">К содержанию</a>
    {pending && <div className="navigation-progress" aria-hidden="true" />}
    <Header kind={kind} />
    <Page key={pathname} pathname={pathname} portal={kind === 'portal'} pending={pending} main={main} />
    {!auth && <Footer />}
    <ScrollRestoration />
  </div>
}

const router = createBrowserRouter([{
  element: <App />,
  hydrateFallbackElement: <main className="portal"><Loading /></main>,
  children: [
    { path: '/', element: <HomePage /> },
    { path: '/login/', element: <LoginPage /> },
    { path: '/reg/', element: <RegisterPage /> },
    { path: '/privacy-policy/', element: <PrivacyPage /> },
    { path: '/profile/', loader: loadResource('profile/'), element: <Gate><AccountPage /></Gate> },
    { path: '/profile/edit/', loader: loadResource('profile/'), element: <Gate><EditProfilePage /></Gate> },
    { path: '/profile/password/', element: <Gate><PasswordPage /></Gate> },
    { path: '/age/', element: <Gate role="child"><QuizzesPage /></Gate> },
    ...Object.entries(quizInfo).flatMap(([key, info]) => {
      const type = key as keyof typeof quizInfo
      return [
        { path: info.path, loader: loadResource(`tests/${type}/`), element: <Gate role="child"><QuizPage type={type} /></Gate> },
        { path: info.result, loader: loadResource(({ request }) => `tests/${type}/results/${new URL(request.url).search}`), element: <Gate role="child"><ResultPage type={type} /></Gate> },
      ]
    }),
    { path: '/signs/', loader: loadResource('signs/'), element: <SignsHomePage /> },
    { path: '/signs/all/', loader: loadResource(({ request }) => 'signs/' + new URL(request.url).search), element: <SignsListPage /> },
    { path: '/signs/:slug/', loader: loadResource(({ params }) => `signs/${encodeURIComponent(params.slug ?? '')}/`), element: <Gate><SignDetailPage /></Gate> },
    { path: '/signs/:slug/test/', loader: loadResource(({ params }) => `signs/${encodeURIComponent(params.slug ?? '')}/test/`), element: <Gate><SignTestPage /></Gate> },
    { path: '/pdd-teacher/', loader: loadResource('lesson-reports/'), element: <Gate role="teacher"><TeacherPage /></Gate> },
    { path: '*', element: <NotFoundPage /> },
  ],
}])

createRoot(document.getElementById('root')!).render(
  <StrictMode><SessionProvider><RouterProvider router={router} /></SessionProvider></StrictMode>,
)
