window.addEventListener('pagereveal', event => {
  if (event.viewTransition) document.documentElement.dataset.nativeMotion = ''
})

document.addEventListener('click', event => {
  const menu = document.querySelector('.admin-mobile-nav[open]')
  if (menu && !menu.contains(event.target)) menu.open = false
})

document.addEventListener('keydown', event => {
  if (event.key !== 'Escape' || document.querySelector('.admin-jump[open]')) return
  const menu = document.querySelector('.admin-mobile-nav[open]')
  if (!menu) return
  menu.open = false
  menu.querySelector('summary').focus()
})

document.addEventListener('DOMContentLoaded', () => {
  const dialog = document.querySelector('#admin-jump')
  const trigger = document.querySelector('.admin-jump-trigger')
  if (!dialog || typeof dialog.showModal !== 'function' || !trigger) return
  const query = dialog.querySelector('#admin-jump-query')
  const empty = dialog.querySelector('.admin-jump-empty')
  const body = dialog.querySelector('.admin-jump-body')
  const normalize = value => value.toLocaleLowerCase('ru').replaceAll('ё', 'е').trim()
  const choices = Array.from(dialog.querySelectorAll('.admin-jump-results li'), row => ({
    row,
    link: row.querySelector('a'),
    search: normalize(row.dataset.keywords + ' ' + row.textContent),
  }))
  let previousFocus
  let pointerStartedOutside = false

  function filter() {
    const terms = normalize(query.value).split(/\s+/).filter(Boolean)
    let count = 0
    for (const { row, search } of choices) {
      row.hidden = !terms.every(term => search.includes(term))
      if (!row.hidden) count++
    }
    empty.hidden = count !== 0
    body.scrollTop = 0
  }

  function open() {
    previousFocus = document.activeElement
    const mobileMenu = document.querySelector('.admin-mobile-nav[open]')
    if (mobileMenu) {
      if (mobileMenu.contains(previousFocus)) previousFocus = mobileMenu.querySelector('summary')
      mobileMenu.open = false
    }
    query.value = ''
    filter()
    dialog.showModal()
    query.focus({ preventScroll: true })
  }

  function outside(event) {
    const { left, right, top, bottom } = dialog.getBoundingClientRect()
    return event.target === dialog && (event.clientX < left || event.clientX > right || event.clientY < top || event.clientY > bottom)
  }

  trigger.hidden = false
  if (/Mac|iPhone|iPad/.test(navigator.platform)) trigger.querySelector('kbd').textContent = '⌘ K'
  trigger.addEventListener('click', open)
  query.addEventListener('input', filter)
  dialog.querySelector('.admin-jump-close').addEventListener('click', () => dialog.close())
  dialog.addEventListener('pointerdown', event => { pointerStartedOutside = outside(event) })
  dialog.addEventListener('click', event => { if (pointerStartedOutside && outside(event)) dialog.close() })
  dialog.addEventListener('close', () => {
    pointerStartedOutside = false
    const target = previousFocus instanceof HTMLElement && previousFocus !== document.body && previousFocus.isConnected ? previousFocus : trigger
    target.focus({ preventScroll: true })
  })

  document.addEventListener('keydown', event => {
    if (event.isComposing || event.altKey || event.shiftKey || !(event.ctrlKey || event.metaKey) || event.code !== 'KeyK') return
    event.preventDefault()
    if (event.repeat) return
    if (dialog.open) dialog.close()
    else open()
  })

  dialog.addEventListener('keydown', event => {
    if (event.isComposing || event.altKey || event.ctrlKey || event.metaKey) return
    if (event.key === 'Escape') {
      event.preventDefault()
      dialog.close()
      return
    }
    const links = choices.filter(({ row }) => !row.hidden).map(({ link }) => link)
    if (!links.length) return
    if (event.key === 'Enter' && event.target === query) {
      event.preventDefault()
      links[0].click()
      return
    }
    if (!['ArrowDown', 'ArrowUp'].includes(event.key)) return
    const index = links.indexOf(event.target)
    if (index < 0 && event.target !== query) return
    event.preventDefault()
    const next = index + (event.key === 'ArrowDown' ? 1 : -1)
    if (next < 0) (event.target === query ? links.at(-1) : query).focus()
    else (links[next] || query).focus()
  })
})
