(() => {
  const root = document.querySelector('#content')
  if (!root || typeof IntersectionObserver === 'undefined') return

  const selector = [
    '.dashboard #content-main > .module', '#content-related > .module',
    '#changelist-filter', '#changelist .paginator', '#result_list tbody tr',
    '#content-main fieldset .form-row', '#content-main .inline-related > h3',
    '#content-main .submit-row', '#change-history tbody tr',
  ].join(',')
  const motion = matchMedia('(prefers-reduced-motion: reduce)')
  const seen = new WeakSet()
  const waiting = new Set()

  function finish(element) {
    if (waiting.delete(element)) observer.unobserve(element)
    delete element.dataset.adminReveal
    element.style.removeProperty('--admin-reveal-delay')
  }

  const observer = new IntersectionObserver(entries => {
    const groups = new Map()
    for (const { target, isIntersecting } of entries) {
      if (!isIntersecting || !waiting.delete(target)) continue
      observer.unobserve(target)
      if (motion.matches || target.matches(':focus-within')) { finish(target); continue }
      const step = groups.get(target.parentElement) || 0
      groups.set(target.parentElement, step + 1)
      target.style.setProperty('--admin-reveal-delay', `${Math.min(step, 3) * 26}ms`)
      target.dataset.adminReveal = 'enter'
    }
  })

  function scan() {
    if (motion.matches) return
    const bottom = document.documentElement.clientHeight
    for (const element of waiting) if (!root.contains(element)) finish(element)
    const next = Array.from(root.querySelectorAll(selector)).filter(element => {
      if (seen.has(element) || element.matches(':focus-within, .errors, :has(.errorlist)')) return false
      const rect = element.getBoundingClientRect()
      if (!rect.height) return false
      seen.add(element)
      return rect.top >= bottom
    })
    for (const element of next) {
      waiting.add(element)
      element.dataset.adminReveal = 'waiting'
      observer.observe(element)
    }
  }

  function expose(event) {
    if (!(event.target instanceof Element)) return
    const target = event.target.closest('[data-admin-reveal]')
    if (target) finish(target)
  }

  motion.addEventListener('change', () => {
    if (motion.matches) root.querySelectorAll('[data-admin-reveal]').forEach(finish)
    else scan()
  })
  root.addEventListener('focusin', expose)
  root.addEventListener('invalid', expose, true)
  root.addEventListener('toggle', scan, true)
  new MutationObserver(records => {
    if (records.some(record => [...record.addedNodes, ...record.removedNodes].some(node => node instanceof Element))) scan()
  }).observe(root, { childList: true, subtree: true })
  scan()
})()
