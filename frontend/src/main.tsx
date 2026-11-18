import { StrictMode, useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { ComponentType, ReactNode, RefObject } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, Navigate, Outlet, RouterProvider, ScrollRestoration, useLocation, useNavigation, useNavigationType, useViewTransitionState } from 'react-router-dom'
import '@fontsource-variable/golos-text'
import './styles.css'
import { loadResource, SessionProvider, useSession } from './state'
import type { Role } from './api'
import { ButtonLink, Footer, Header, Loading, LoadError, PortalHeading } from './ui'
import { LoginPage, RegisterPage } from './public-pages'
import { HomePage } from './landing'
import { quizInfo } from './quiz-info'
import { useViewportMotion } from './viewport-motion'
import { MotionProvider, useMotionSettings } from './motion-settings'
import privacyText from './privacy.html?raw'

function Gate({ children, role }: { children: ReactNode; role?: Role }) {
  const { user, error, refresh } = useSession()
  const location = useLocation()
  if (error && user === undefined) return <LoadError error={error} retry={refresh} />
  if (user === undefined) return <Loading />
  if (!user) return <Navigate to="/login/" state={{ next: location.pathname + location.search + location.hash }} replace />
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
  const { pathname, hash, key } = useLocation()
  const navigation = useNavigationType()
  const pending = useNavigation().state !== 'idle'
  const site = useRef<HTMLDivElement>(null)
  const main = useRef<HTMLElement>(null)
  const previousPath = useRef(pathname)
  const previousIndex = useRef<number | undefined>(window.history.state?.idx)
  const home = pathname === '/'
  const sectionNavigation = home && !!hash && navigation !== 'POP'
  const auth = /^\/(login|reg)\/?$/.test(pathname)
  const kind = home ? 'home' : auth ? 'auth' : 'portal'
  const { enabled } = useMotionSettings()
  useViewportMotion(site, pathname, enabled)

  useLayoutEffect(() => {
    const index: number | undefined = window.history.state?.idx
    const back = navigation === 'POP'
      ? index !== undefined && previousIndex.current !== undefined && index < previousIndex.current
      : pathname !== previousPath.current && previousPath.current.startsWith(pathname.endsWith('/') ? pathname : pathname + '/')
    if (site.current) site.current.dataset.direction = back ? 'back' : 'forward'
    previousIndex.current = index
  }, [key, pathname, navigation])

  useEffect(() => {
    if (sectionNavigation) document.getElementById(hash.slice(1))?.focus({ preventScroll: true })
  }, [sectionNavigation, hash, key])

  useEffect(() => {
    const changed = previousPath.current !== pathname
    previousPath.current = pathname
    if (changed && navigation !== 'POP') main.current?.focus({ preventScroll: true })
    const title = main.current?.querySelector('h1')?.textContent
    document.title = title && !home ? title + ' — Знай ПДД' : 'Знай ПДД'
  }, [pathname, home, navigation])

  return <div ref={site} className={`site site-${kind}`} data-motion={enabled ? 'on' : 'off'}
    data-section-navigation={sectionNavigation || undefined}>
    <a className="skip-link" href="#main">К содержанию</a>
    {pending && <div className="navigation-progress" aria-hidden="true" />}
    <Header kind={kind} />
    <Page key={pathname} pathname={pathname} portal={kind === 'portal'} pending={pending} main={main} />
    {!auth && <Footer />}
    <ScrollRestoration />
  </div>
}

const account = () => import('./account-pages')
const quizzes = () => import('./quiz-pages')
const signs = () => import('./sign-pages')
const practice = () => import('./practice-pages')
const news = () => import('./news-pages')
const classroom = () => import('./classroom-pages')
const classroomTests = () => import('./classroom-tests')
const joining = () => import('./classroom-join')

function lazyPage(load: () => Promise<ComponentType>, gate?: true | Role) {
  return async () => {
    const Component = await load()
    return { element: gate ? <Gate role={gate === true ? undefined : gate}><Component /></Gate> : <Component /> }
  }
}

const router = createBrowserRouter([{
  element: <App />,
  hydrateFallbackElement: <main className="portal"><Loading /></main>,
  children: [
    { path: '/', element: <HomePage /> },
    { path: '/road-circuit/', lazy: lazyPage(() => import('./road-circuit').then(module => module.RoadCircuitPage)) },
    { path: '/login/', element: <LoginPage /> },
    { path: '/reg/', element: <RegisterPage /> },
    { path: '/join/', lazy: lazyPage(() => joining().then(m => m.JoinPage)) },
    { path: '/join/:code/', loader: loadResource(({ params }) => 'classroom/join/' + params.code + '/'),
      lazy: lazyPage(() => joining().then(m => m.JoinSessionPage)) },
    ...['/classroom/', '/classroom/history/'].map(path => ({ path, loader: loadResource('classroom/'),
      lazy: lazyPage(() => classroom().then(m => m.ClassroomPage), 'teacher') })),
    ...['/classroom/runs/:id/', '/classroom/runs/:id/report/'].map(path => ({ path,
      loader: loadResource(({ params }) => 'classroom/runs/' + params.id + '/'),
      lazy: lazyPage(() => classroom().then(m => m.ClassroomRunPage), 'teacher') })),
    { path: '/classroom/tests/', loader: loadResource('classroom/tests/'), lazy: lazyPage(() => classroomTests().then(m => m.ClassroomTestsPage), 'teacher') },
    { path: '/classroom/tests/:id/', loader: loadResource(({ params }) => 'classroom/tests/' + params.id + '/'),
      lazy: lazyPage(() => classroomTests().then(m => m.ClassroomTestPage), 'teacher') },
    { path: '/privacy-policy/', element: <PrivacyPage /> },
    { path: '/profile/', loader: loadResource('profile/'), lazy: lazyPage(() => account().then(module => module.AccountPage), true) },
    { path: '/profile/edit/', loader: loadResource('profile/'), lazy: lazyPage(() => account().then(module => module.EditProfilePage), true) },
    { path: '/profile/password/', lazy: lazyPage(() => account().then(module => module.PasswordPage), true) },
    { path: '/age/', lazy: lazyPage(() => quizzes().then(module => module.QuizzesPage), 'child') },
    ...Object.entries(quizInfo).flatMap(([key, info]) => {
      const type = key as keyof typeof quizInfo
      return [
        { path: info.path, loader: loadResource(`tests/${type}/`),
          lazy: lazyPage(() => quizzes().then(({ QuizPage }) => () => <QuizPage type={type} />), 'child') },
        { path: info.result, loader: loadResource(({ request }) => `tests/${type}/results/${new URL(request.url).search}`),
          lazy: lazyPage(() => quizzes().then(({ ResultPage }) => () => <ResultPage type={type} />), 'child') },
      ]
    }),
    ...['/signs/', '/signs/all/'].map(path => ({
      path, loader: loadResource(({ request }) => 'signs/' + new URL(request.url).search),
      lazy: lazyPage(() => signs().then(module => module.SignsListPage)),
    })),
    { path: '/safe-route/', loader: loadResource('safe-route/'),
      lazy: lazyPage(() => import('./safe-route-page').then(module => module.SafeRoutePage)) },
    { path: '/rating/', loader: loadResource(({ request }) => 'rating/' + new URL(request.url).search),
      lazy: lazyPage(() => import('./rating-page').then(module => module.RatingPage), true) },
    { path: '/practice/', loader: loadResource(({ request }) => 'practice/' + new URL(request.url).search),
      lazy: lazyPage(() => practice().then(module => module.PracticePage)) },
    { path: '/practice/history/', loader: loadResource('practice/history/'),
      lazy: lazyPage(() => practice().then(module => module.PracticeHistoryPage), true) },
    { path: '/practice/:slug/', loader: loadResource(({ params, request }) => 'practice/' + encodeURIComponent(params.slug ?? '') + '/' + new URL(request.url).search),
      lazy: lazyPage(() => practice().then(module => module.PracticeExercisePage)) },
    { path: '/news/', loader: loadResource(({ request }) => 'news/' + new URL(request.url).search),
      lazy: lazyPage(() => news().then(module => module.NewsPage)) },
    { path: '/news/:slug/', loader: loadResource(({ params }) => 'news/' + encodeURIComponent(params.slug ?? '') + '/'),
      lazy: lazyPage(() => news().then(module => module.NewsPostPage)) },
    { path: '/signs/:slug/', loader: loadResource(({ params }) => `signs/${encodeURIComponent(params.slug ?? '')}/`),
      lazy: lazyPage(() => signs().then(module => module.SignDetailPage)) },
    { path: '/signs/:slug/test/', loader: loadResource(({ params }) => `signs/${encodeURIComponent(params.slug ?? '')}/test/`),
      lazy: lazyPage(() => signs().then(module => module.SignTestPage), true) },
    { path: '/pdd-teacher/', lazy: async () => {
      const { loadLessonReports, TeacherPage } = await account()
      return { loader: loadLessonReports, element: <Gate role="teacher"><TeacherPage /></Gate> }
    } },
    { path: '/pdd-teacher/:id/', lazy: async () => {
      const { loadLessonReports, TeacherReportPage } = await account()
      return { loader: loadLessonReports, element: <Gate role="teacher"><TeacherReportPage /></Gate> }
    } },
    { path: '*', element: <NotFoundPage /> },
  ],
}])

createRoot(document.getElementById('root')!).render(
  <StrictMode><MotionProvider><SessionProvider><RouterProvider router={router} /></SessionProvider></MotionProvider></StrictMode>,
)
