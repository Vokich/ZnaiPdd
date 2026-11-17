import { useEffect, useRef } from 'react'
import { useInView } from 'motion/react'

type Context = CanvasRenderingContext2D
export type RouteScene = {
  label: string; text: string; kind: string; travel: 'walk' | 'walk-bike' | 'ride'
}

const width = 720
const height = 350
export const walkTime = 1100
const crossings = new Set(['signal', 'zebra', 'visibility', 'island', 'ambulance', 'diagonal', 'dismount', 'bike_signal', 'bike_yield'])

function box(ctx: Context, x: number, y: number, w: number, h: number, radius: number, color: string) {
  ctx.fillStyle = color
  ctx.beginPath()
  ctx.roundRect(x, y, w, h, radius)
  ctx.fill()
}

function dot(ctx: Context, x: number, y: number, size: number, color: string) {
  ctx.fillStyle = color
  ctx.beginPath()
  ctx.arc(x, y, size, 0, Math.PI * 2)
  ctx.fill()
}

function line(ctx: Context, x: number, y: number, endX: number, endY: number, size: number, color: string) {
  ctx.strokeStyle = color
  ctx.lineWidth = size
  ctx.lineCap = 'round'
  ctx.beginPath()
  ctx.moveTo(x, y)
  ctx.lineTo(endX, endY)
  ctx.stroke()
}

function tree(ctx: Context, x: number, y: number, size = 1) {
  dot(ctx, x + 5, y + 7, 16 * size, '#b6c899')
  dot(ctx, x - 5 * size, y - 4 * size, 12 * size, '#9cbd83')
  dot(ctx, x + 6 * size, y - 7 * size, 13 * size, '#9cbd83')
  line(ctx, x, y + 22 * size, x, y - 3 * size, 3 * size, '#617e6a')
  line(ctx, x, y + 6 * size, x + 7 * size, y, 2 * size, '#617e6a')
}

function building(ctx: Context, x: number, y: number, school = false) {
  const w = school ? 112 : 82
  box(ctx, x + 11, y + 9, w + 8, 66, 0, '#d7b197')
  box(ctx, x, y, w, 74, 0, school ? '#ffe199' : '#ffe3ad')
  ctx.fillStyle = '#2e5aa7'
  ctx.beginPath()
  ctx.moveTo(x - 6, y + 2)
  ctx.lineTo(x + 12, y - 17)
  ctx.lineTo(x + w - 6, y - 17)
  ctx.lineTo(x + w + 14, y + 2)
  ctx.closePath()
  ctx.fill()
  for (let dx = 12; dx < w - 9; dx += 22) {
    box(ctx, x + dx, y + 12, 10, 13, 0, '#2e5aa7')
    box(ctx, x + dx, y + 34, 10, 15, 0, '#9e809f')
  }
  box(ctx, x + w / 2 - 7, y + 54, 14, 20, 1, '#486489')
  if (school) dot(ctx, x + w / 2, y - 8, 5, '#ffe099')
}

function vehicle(ctx: Context, x: number, y: number, color: string, kind = 'car', reverse = false, flashing = false) {
  const w = kind === 'bus' ? 116 : kind === 'ambulance' ? 84 : 66
  ctx.save()
  ctx.translate(x, y)
  if (reverse) ctx.scale(-1, 1)
  box(ctx, -w / 2 - 1, -9, w + 6, 29, 9, '#26394160')
  for (const dx of [-w / 2 + 8, w / 2 - 16]) {
    box(ctx, dx, -14, 10, 29, 3, '#202d38')
  }
  box(ctx, -w / 2, -12, w, 25, 8, color)
  box(ctx, -w / 2 + 12, -8, w - 28, 17, 5, '#d6edf4')
  box(ctx, -w / 2 + 15, -7, w - 39, 15, 3, color)
  box(ctx, w / 2 - 10, -9, 7, 5, 2, '#fff0b2')
  box(ctx, w / 2 - 10, 4, 7, 5, 2, '#fff0b2')
  if (kind === 'ambulance') {
    line(ctx, -10, 0, 2, 0, 3, '#a63738')
    line(ctx, -4, -6, -4, 6, 3, '#a63738')
    box(ctx, 11, -14, 9, 5, 2, flashing ? '#a3edff' : '#3379c3')
  }
  ctx.restore()
}

function signal(ctx: Context, x: number, y: number, green: boolean, bicycle = false) {
  line(ctx, x + 11, y + 34, x + 11, y + 60, 5, '#283b46')
  box(ctx, x, y, 22, 42, 6, '#23313f')
  dot(ctx, x + 11, y + 12, 6, green ? '#824948' : '#ff6b64')
  dot(ctx, x + 11, y + 30, 6, green ? '#94f696' : '#487660')
  if (bicycle) {
    box(ctx, x - 1, y + 45, 24, 15, 3, '#f7f5e5')
    bike(ctx, x + 11, y + 52, .28, '#263641')
  }
}

function bike(ctx: Context, x: number, y: number, scale = 1, color = '#1d425d') {
  ctx.save()
  ctx.translate(x, y)
  ctx.scale(scale, scale)
  dot(ctx, -15, 0, 8.5, color)
  dot(ctx, 15, 0, 8.5, color)
  dot(ctx, -15, 0, 6, '#dce9e4')
  dot(ctx, 15, 0, 6, '#dce9e4')
  line(ctx, -15, 0, -3, -10, 2.5, color)
  line(ctx, -15, 0, 0, 0, 2.5, color)
  line(ctx, -3, -10, 0, 0, 2.5, color)
  line(ctx, 0, 0, 10, -11, 2.5, color)
  line(ctx, -3, -10, 10, -11, 2.5, color)
  line(ctx, 10, -11, 15, 0, 2.5, color)
  line(ctx, 9, -15, 14, -15, 2.5, color)
  ctx.restore()
}

function character(ctx: Context, x: number, y: number, step: number, travel: RouteScene['travel']) {
  ctx.save()
  ctx.translate(x, y)
  box(ctx, -13, -1, 29, 6, 3, '#243e3e35')
  if (travel === 'ride') bike(ctx, 0, -5)
  if (travel === 'walk-bike') bike(ctx, 24, -7, .8)
  const shift = Math.sin(step) * 6
  const bodyY = travel === 'ride' ? -7 : 0
  const feetY = travel === 'ride' ? -13 : 0
  line(ctx, -4, bodyY - 16, -5 + shift, feetY, 5, '#213e61')
  line(ctx, 3, bodyY - 16, 5 - shift, feetY, 5, '#243c53')
  line(ctx, -8 + shift, feetY, -3 + shift, feetY, 4, '#172d40')
  line(ctx, 4 - shift, feetY, 9 - shift, feetY, 4, '#172d40')
  box(ctx, -12, bodyY - 34, 10, 19, 4, '#81528e')
  box(ctx, -8, bodyY - 34, 17, 21, 6, '#e88535')
  line(ctx, 5, bodyY - 29, travel === 'walk' ? 8 + shift : 15, bodyY - 16, 4, '#efae54')
  dot(ctx, 1, bodyY - 40, 8, '#f5c392')
  if (travel === 'ride') box(ctx, -9, bodyY - 47, 22, 7, 4, '#3977a7')
  else box(ctx, -7, bodyY - 48, 15, 7, 4, '#654337')
  ctx.restore()
}

function drawStreet(ctx: Context, scene: RouteScene, time: number, progress: number, destination: string | null) {
  const { kind } = scene
  const across = crossings.has(kind)
  const bikeTrack = scene.travel === 'ride' && kind !== 'dismount'
  const starting = kind === 'home' || kind === 'school'
  const alongPath = starting || ['park', 'walkway', 'works', 'bike_crowd'].includes(kind)
  ctx.fillStyle = '#dce9cb'
  ctx.fillRect(0, 0, width, height)
  box(ctx, -20, 25, 278, 108, 25, '#d4e4bb')
  box(ctx, 449, 264, 263, 65, 22, '#d0e0b7')
  box(ctx, 476, 17, 284, 112, 25, '#d4e4bb')
  building(ctx, 80, 36, kind === 'school')
  building(ctx, 174, 57)
  building(ctx, 517, 37)
  building(ctx, 614, 56)
  for (const [x, y, size] of [[35, 42, 1.1], [229, 46, .8], [290, 77, 1.1], [505, 43, .9], [684, 97, .85], [60, 302, 1.15], [160, 300, .8], [604, 307, .9], [692, 299, 1.1]]) {
    tree(ctx, x, y, size)
  }

  if (alongPath) {
    box(ctx, -14, 137, 750, 90, 10, '#a9bd92')
    box(ctx, -14, 155, 750, 58, 9, kind === 'works' ? '#d4ceb0' : '#eae4cb')
    if (kind === 'works') {
      line(ctx, 330, 185, 560, 185, 12, '#ce7860')
      for (let x = 345; x < 560; x += 26) line(ctx, x, 180, x + 8, 189, 5, '#fff1cf')
      line(ctx, 345, 181, 345, 210, 5, '#8d5f47')
      line(ctx, 548, 181, 548, 210, 5, '#8d5f47')
    }
    if (kind === 'bike_crowd') {
      for (const [x, y] of [[401, 191], [434, 181], [455, 205]]) character(ctx, x, y, 0, 'walk')
    }
  } else {
    const sidewalk = kind === 'shoulder' ? '#d9bf9a' : '#f2d2b1'
    box(ctx, -20, 233, 760, 117, 0, '#f7d6b6')
    for (const [x, y] of [[68, 309], [647, 310]]) tree(ctx, x, y, .84)
    box(ctx, -20, 104, 760, 160, 0, sidewalk)
    box(ctx, -20, 131, 760, 107, 0, '#415b80')
    for (let x = 12; x < 720; x += 36) {
      if (!across || x < 305 || x > 394) line(ctx, x, 183, x + 13, 183, 2, '#c5d9ec')
    }
    if (bikeTrack) {
      box(ctx, -20, 242, 760, 24, 0, '#568e7c')
      for (const x of [106, 280, 519, 657]) bike(ctx, x, 255, .36, '#f1f9e8')
    }
    if (across) {
      for (let y = 136; y < 235; y += 13) {
        if (!bikeTrack) box(ctx, 329, y, 65, 7, 1, '#fffdfa')
        else for (const x of [336, 383]) box(ctx, x, y, 6, 7, 1, '#fffdfa')
      }
    }
    if (kind === 'island') box(ctx, 315, 173, 94, 22, 8, '#e8cf86')
    if (kind === 'underpass') {
      box(ctx, 322, 243, 76, 38, 6, '#2e4455')
      for (let y = 248; y < 279; y += 6) line(ctx, 333, y, 387, y, 2, '#acbdaf')
      for (let x = 10; x < 720; x += 24) line(ctx, x, 179, x + 18, 179, 4, '#e5c88c')
    }
    if (kind === 'signal' || kind === 'diagonal' || kind === 'bike_signal') {
      signal(ctx, 443, 203, progress > .25, kind === 'bike_signal')
      if (kind === 'bike_signal') signal(ctx, 486, 201, true)
    }
    const travelX = (time * .09 + 151) % 890 - 85
    if (kind === 'ambulance' && progress > 0) {
      vehicle(ctx, 120 + progress * 2400, 157, '#fff4df', 'ambulance', false, true)
      vehicle(ctx, 472, 211, '#85b3cf', 'car', true)
    } else if (progress < .24 || !across) {
      vehicle(ctx, travelX, 157, kind === 'ambulance' ? '#fff4df' : '#f6f4ed',
        kind === 'ambulance' ? 'ambulance' : 'car', false, Math.floor(time / 380) % 2 === 0)
      vehicle(ctx, 720 - (travelX + 250) % 850, 211, '#85b3cf', 'car', true)
    } else {
      vehicle(ctx, 258, 157, '#f6f4ed')
      vehicle(ctx, 472, 211, '#85b3cf', 'car', true)
    }
    if (kind === 'visibility') vehicle(ctx, 277, 218, '#e18e63', 'bus')
    if (kind === 'diagonal') {
      box(ctx, 542, 0, 63, 132, 0, '#415b80')
      line(ctx, 573, 0, 573, 85, 2, '#f0e4b7')
      for (let x = 548; x < 599; x += 10) box(ctx, x, 106, 5, 18, 0, '#faf3db')
      signal(ctx, 507, 71, progress > .65)
    }
  }

  const step = progress * Math.PI * 8
  const travel = ['dismount', 'bike_crowd'].includes(kind) && progress > .13 ? 'walk-bike' : scene.travel
  if (kind === 'diagonal') {
    const forward = Math.max(0, Math.min(1, (progress - .2) / .45))
    const turn = Math.max(0, (progress - .65) / .35)
    character(ctx, 367 + turn * 270, 285 - forward * 168, step, travel)
  } else if (across) {
    const fraction = Math.max(0, (progress - .25) / .75)
    const y = kind === 'island' ? 183 : bikeTrack ? 263 : 285
    character(ctx, 367, y - fraction * (y - 120), step, travel)
  } else if (kind === 'underpass') {
    character(ctx, 360, 306 - progress * 55, step, travel)
  } else if (alongPath) {
    const bend = destination === 'park' ? -1 : 1
    const y = kind === 'works' ? 192 + bend * Math.sin(progress * Math.PI) * 55 : 194
    character(ctx, 205 + progress * 250, y, step, travel)
  } else {
    character(ctx, 222 + progress * 250, bikeTrack ? 266 : 264, step, travel)
  }
}

export function RouteStreet({ scene, destination, paused }: { scene: RouteScene; destination: string | null; paused: boolean }) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const visible = useInView(canvas)
  useEffect(() => {
    const node = canvas.current
    const ctx = node?.getContext('2d')
    if (!node || !ctx) return
    const density = Math.min(window.devicePixelRatio || 1, 2)
    node.width = width * density
    node.height = height * density
    ctx.scale(density, density)
    let frame = 0
    let started: number | undefined
    let lastDraw = -Infinity
    function render(time: number) {
      if (!ctx) return
      started ??= time
      if (time - lastDraw >= 28) {
        const elapsed = time - started
        drawStreet(ctx, scene, elapsed, destination ? Math.min(1, elapsed / walkTime) : 0, destination)
        lastDraw = time
      }
      if (!paused && (visible || destination)) frame = requestAnimationFrame(render)
    }
    render(performance.now())
    return () => cancelAnimationFrame(frame)
  }, [scene, destination, paused, visible])
  return <canvas ref={canvas} className="route-street" aria-hidden="true" />
}
