/* EduPath AI — main.js */

document.addEventListener('DOMContentLoaded', () => {

  // ── Range slider labels ──
  document.querySelectorAll('input[type=range]').forEach(r => {
    const display = document.getElementById(r.id + '_val') || r.nextElementSibling;
    if (display) display.textContent = r.value + '%';
    r.addEventListener('input', () => {
      if (display) display.textContent = r.value + '%';
    });
  });

  // ── Tab system ──
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const group = btn.closest('[data-tab-group]')?.dataset.tabGroup || 'default';
      const target = btn.dataset.tab;

      document.querySelectorAll(`.tab-btn[data-tab-group="${group}"], .tab-btn:not([data-tab-group])`).forEach(b => {
        if (b.closest('[data-tab-group]')?.dataset.tabGroup === group || !b.closest('[data-tab-group]')) {
          b.classList.remove('active');
        }
      });
      document.querySelectorAll(`.tab-panel`).forEach(p => {
        if (p.dataset.tabGroup === group || (!p.dataset.tabGroup && group === 'default')) {
          p.classList.remove('active');
        }
      });

      btn.classList.add('active');
      const panel = document.getElementById('tab-' + target);
      if (panel) panel.classList.add('active');
    });
  });

  // ── Reminder mark-read ──
  document.querySelectorAll('.js-mark-read').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.dataset.id;
      const res = await fetch(`/student/reminder/read/${id}`, { method: 'POST' });
      if (res.ok) {
        const item = btn.closest('.reminder-item');
        if (item) {
          item.classList.add('read');
          const dot = item.querySelector('.reminder-item__dot');
          if (dot) dot.style.background = 'var(--sand)';
          btn.remove();
        }
        // update badge
        const badge = document.querySelector('.nav-badge');
        if (badge) {
          const cnt = parseInt(badge.textContent) - 1;
          if (cnt <= 0) badge.remove();
          else badge.textContent = cnt;
        }
      }
    });
  });

  // ── Toasts from flash messages ──
  const flashMsgs = document.querySelectorAll('[data-flash]');
  flashMsgs.forEach(el => {
    showToast(el.dataset.flash, el.dataset.flashType || 'info');
    el.remove();
  });

  // ── Course institution dynamic load ──
  const instSelect = document.getElementById('institution_id');
  const courseSelect = document.getElementById('course_id');
  if (instSelect && courseSelect) {
    instSelect.addEventListener('change', async () => {
      const instId = instSelect.value;
      if (!instId) { courseSelect.innerHTML = '<option value="">— Select course —</option>'; return; }
      const res = await fetch(`/api/courses/${instId}`);
      const courses = await res.json();
      courseSelect.innerHTML = '<option value="">— No specific course —</option>' +
        courses.map(c => `<option value="${c.id}">${c.title} (${c.qualification})</option>`).join('');
    });
  }

  // ── Confirm deletes ──
  document.querySelectorAll('[data-confirm]').forEach(btn => {
    btn.addEventListener('click', e => {
      if (!confirm(btn.dataset.confirm)) e.preventDefault();
    });
  });

  // ── Auto-hide alerts ──
  setTimeout(() => {
    document.querySelectorAll('.alert-auto-hide').forEach(el => {
      el.style.transition = 'opacity .5s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 500);
    });
  }, 4000);

});

function showToast(msg, type = 'info') {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.transition = 'opacity .4s';
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 400);
  }, 3500);
}

// ── Simple markdown to HTML (for report display) ──
function renderMarkdown(raw) {
  return raw
    .replace(/^## (.+)$/gm,  '<h2>$1</h2>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^#### (.+)$/gm,'<h4>$1</h4>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,    '<em>$1</em>')
    .replace(/^---$/gm,       '<hr>')
    .replace(/^[-•]\s(.+)$/gm,'<li>$1</li>')
    .replace(/(<li>.*<\/li>)/gs, m => `<ul>${m}</ul>`)
    .replace(/^\d+\.\s(.+)$/gm, '<li>$1</li>')
    .replace(/\n{2,}/g, '</p><p>')
    .replace(/^(?!<[h|u|l|h|p|d])(.+)$/gm, p => p ? `<p>${p}</p>` : '');
}

document.querySelectorAll('.md-render').forEach(el => {
  if (el.dataset.raw) {
    el.innerHTML = renderMarkdown(el.dataset.raw);
  }
});
