document.addEventListener('DOMContentLoaded', () => {
  let hoverTimer
  let defaultErrorMessage = 'Server error, plesae try again later.'

  let deleteModal = document.getElementById('delete-modal')
  let deleteForm = document.querySelector('.delete-form')

  if (deleteModal && deleteForm) {
    deleteModal.addEventListener('show.bs.modal', event => {
      deleteForm.setAttribute('action', event.relatedTarget.dataset.href)
    })
  }

  let descriptionBtn = document.getElementById('description-btn')
  let cancelDescription = document.getElementById('cancel-description')
  let description = document.getElementById('description')
  let descriptionForm = document.getElementById('description-form')

  descriptionBtn &&
    descriptionBtn.addEventListener('click', () => {
      description.style.display = 'none'
      descriptionForm.style.display = 'block'
    })

  cancelDescription &&
    cancelDescription.addEventListener('click', () => {
      descriptionForm.style.display = 'none'
      description.style.display = 'block'
    })

  document.querySelectorAll('.profile-popover').forEach(el => {
    el.addEventListener('mouseenter', showProfilePopover)
    el.addEventListener('mouseleave', hideProfilePopover)
  })

  function showProfilePopover(event) {
    let el = event.target
    hoverTimer = setTimeout(async () => {
      hoverTimer = null
      try {
        let res = await fetch(el.dataset.href)
        let data = await res.text()
        let popover = bootstrap.Popover.getOrCreateInstance(el, {
          content: data,
          html: true,
          sanitize: false,
          trigger: 'manual',
        })
        popover.setContent({ '.popover-body': data })
        popover.show()
        document
          .querySelector('.popover')
          .addEventListener('mouseleave', () => {
            setTimeout(() => {
              popover.hide()
            }, 200)
          })
      } catch (error) {
        handleFetchError(error)
      }
    }, 500)
  }

  function hideProfilePopover(event) {
    let el = event.target
    if (hoverTimer) {
      clearTimeout(hoverTimer)
      hoverTimer = null
    } else {
      setTimeout(() => {
        if (!document.querySelector('.popover:hover')) {
          let popover = bootstrap.Popover.getInstance(el)
          popover.hide()
        }
      }, 200)
    }
  }

  function handleFetchError(error) {
    console.error('Fetch error:', error)
    let message = defaultErrorMessage
    if (error.response && error.response.hasOwnProperty('message')) {
      message = error.response.message
    }
    toast(message, 'error')
  }

  function toast(body, category) {
    let toastEl = document.getElementById('mainToast')
    let toast = bootstrap.Toast.getOrCreateInstance(toastEl)
    toastEl.querySelector('.toast-body').textContent = body
    if (category === 'error') {
      toastEl.classList.replace('text-bg-secondary', 'text-bg-danger')
    } else {
      toastEl.classList.replace('text-bg-danger', 'text-bg-secondary')
    }
    toast.show()
  }

  async function follow(event) {
    let el = event.target
    let id = el.dataset.id
    try {
      let res = await fetch(el.dataset.href, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
      })
      let data = await res.json()
      el.previousElementSibling.style.display = 'inline-block'
      el.style.display = 'none'
      updateFollowersCount(id)
      toast(data.message)
    } catch (error) {
      handleFetchError(error)
    }
  }

  async function unfollow(event) {
    let el = event.target
    let id = el.dataset.id
    try {
      let res = await fetch(el.dataset.href, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
      })
      let data = await res.json()
      el.nextElementSibling.style.display = 'inline-block'
      el.style.display = 'none'
      updateFollowersCount(id)
      toast(data.message)
    } catch (error) {
      handleFetchError(error)
    }
  }

  async function collect(event) {
    let el = event.target
    while (el && !el.classList.contains('collect-btn')) {
      el = el.parentElement
    }
    let id = el.dataset.id
    try {
      let res = await fetch(el.dataset.href, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
      })
      let data = await res.json()
      el.previousElementSibling.style.display = 'block'
      el.style.display = 'none'
      updateCollectorsCount(id)
      toast(data.message)
    } catch (error) {
      handleFetchError(error)
    }
  }

  async function uncollect(event) {
    let el = event.target
    while (el && !el.classList.contains('uncollect-btn')) {
      el = el.parentElement
    }
    let id = el.dataset.id
    try {
      let res = await fetch(el.dataset.href, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
      })
      let data = await res.json()
      el.nextElementSibling.style.display = 'block'
      el.style.display = 'none'
      updateCollectorsCount(id)
      toast(data.message)
    } catch (error) {
      handleFetchError(error)
    }
  }

  dayjs.extend(window.dayjs_plugin_relativeTime)
  dayjs.extend(window.dayjs_plugin_utc)
  dayjs.extend(window.dayjs_plugin_localizedFormat)

  function renderAllDatetime() {
    // render normal time
    const elements = document.querySelectorAll('.dayjs')
    elements.forEach(elem => {
      const date = dayjs.utc(elem.innerHTML)
      const format = elem.dataset.format ?? 'LL'
      elem.innerHTML = date.local().format(format)
    })
    // render from now time
    const fromNowElements = document.querySelectorAll('.dayjs-from-now')
    fromNowElements.forEach(elem => {
      const date = dayjs.utc(elem.innerHTML)
      elem.innerHTML = date.local().fromNow()
    })
    // render tooltip time
    const toolTipElements = document.querySelectorAll('.dayjs-tooltip')
    toolTipElements.forEach(elem => {
      const date = dayjs.utc(elem.dataset.timestamp)
      const format = elem.dataset.format ?? 'LLL'
      elem.dataset.bsTitle = date.local().format(format)
      const tooltip = new bootstrap.Tooltip(elem)
    })
  }

  document.addEventListener('click', event => {
    if (event.target.classList.contains('follow-btn')) {
      follow(event)
    } else if (event.target.classList.contains('unfollow-btn')) {
      unfollow(event)
    }
  })

  if (document.getElementsByClassName('collect-btn')) {
    document
      .querySelectorAll('.collect-btn')
      .forEach(el => el.addEventListener('click', collect))
  }

  if (document.getElementsByClassName('uncollect-btn')) {
    document
      .querySelectorAll('.uncollect-btn')
      .forEach(el => el.addEventListener('click', uncollect))
  }

  if (document.getElementById('tag-btn')) {
    document.getElementById('.tag-btn').addEventListener('click', () => {
      document.getElementById('tags').style.display = 'none'
      document.getElementById('tag-form').style.display = 'block'
    })
  }

  if (document.getElementById('cancel-tag')) {
    document.getElementById('.cancel-tag').addEventListener('click', () => {
      document.getElementById('tag-form').style.display = 'none'
      document.getElementById('tags').style.display = 'block'
    })
  }

  async function updateFollowersCount(id) {
    let el = document.getElementById('followers-count-' + id)
    try {
      let res = await fetch(el.dataset.href)
      let data = await res.json()
      el.textContent = data.count
    } catch (error) {
      handleFetchError(error)
    }
  }

  async function updateCollectorsCount(id) {
    let el = document.getElementById('collectors-count-' + id)
    try {
      let res = await fetch(el.dataset.href)
      let data = await res.json()
      el.textContent = data.count
    } catch (error) {
      handleFetchError(error)
    }
  }

  async function updateNotificationsCount() {
    let el = document.getElementById('notification-badge')
    if (!el) return
    try {
      let res = await fetch(el.dataset.href)
      let data = await res.json()
      if (data.count === 0) {
        el.style.display = 'none'
      } else {
        el.style.display = 'block'
        el.textContent = data.count
      }
    } catch (error) {
      handleFetchError(error)
    }
  }

  isAuthenticated && setInterval(updateNotificationsCount, 30 * 1000)

  let tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="tooltip"]')
  )
  let tooltipList = tooltipTriggerList.map(el => new bootstrap.Tooltip(el))

  renderAllDatetime()
})
