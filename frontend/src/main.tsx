import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import '@fontsource-variable/golos-text'
import './styles/styles.css'
import { router } from './app/router'
import { MotionProvider } from './shared/motion/motion-settings'
import { SessionProvider } from './shared/state'

createRoot(document.getElementById('root')!).render(
  <StrictMode><MotionProvider><SessionProvider><RouterProvider router={router} /></SessionProvider></MotionProvider></StrictMode>,
)
