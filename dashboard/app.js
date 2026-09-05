// KernelDeck Dashboard Client
// Protocol reference: PROTOCOL.md

const hardwareStatusEl = document.getElementById('hardware-status');
const currentGateEl = document.getElementById('current-gate');
const auditLogEl = document.getElementById('audit-log');

let resetGateTimeout = null;

function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.hostname || 'localhost';
  const port = window.location.port || '8080';
  const wsUrl = `${protocol}//${host}:${port}/ws/dashboard`;

  const socket = new WebSocket(wsUrl);

  socket.addEventListener('open', () => {
    console.log('[KernelDeck] Connected to dashboard WebSocket');
  });

  socket.addEventListener('message', (event) => {
    try {
      const msg = JSON.parse(event.data);
      handleMessage(msg);
    } catch (err) {
      console.error('[KernelDeck] Failed to parse message:', err, event.data);
    }
  });

  socket.addEventListener('close', () => {
    console.warn('[KernelDeck] WebSocket closed, retrying in 2s...');
    updateHardwareStatus(false);
    setTimeout(connectWebSocket, 2000);
  });

  socket.addEventListener('error', (err) => {
    console.error('[KernelDeck] WebSocket error:', err);
  });
}

function handleMessage(msg) {
  if (msg.type === 'SYSTEM_STATUS') {
    // Protocol Section 2: { type: "SYSTEM_STATUS", hardware_connected: boolean }
    updateHardwareStatus(Boolean(msg.hardware_connected));
  } else if (msg.type === 'AUDIT_EVENT') {
    // Protocol Section 2: { type: "AUDIT_EVENT", request_id, timestamp, event, cmd, verdict, rule }
    handleAuditEvent(msg);
  }
}

function updateHardwareStatus(connected) {
  if (connected) {
    hardwareStatusEl.textContent = '? CONNECTED';
    hardwareStatusEl.className = 'status-badge connected';
  } else {
    hardwareStatusEl.textContent = '? DISCONNECTED';
    hardwareStatusEl.className = 'status-badge disconnected';
  }
}

function handleAuditEvent(event) {
  if (resetGateTimeout) {
    clearTimeout(resetGateTimeout);
    resetGateTimeout = null;
  }

  if (event.event === 'CHALLENGE_ISSUED') {
    currentGateEl.textContent = event.cmd ? event.cmd : 'CHALLENGE ISSUED';
    currentGateEl.style.color = '#ff7b72';
  } else if (event.event === 'VERDICT_RECEIVED') {
    currentGateEl.textContent = `VERDICT: ${event.verdict}`;
    currentGateEl.style.color = event.verdict === 'ALLOW' ? '#3fb950' : '#f85149';
    resetGateTimeout = setTimeout(() => {
      currentGateEl.textContent = 'NONE';
      currentGateEl.style.color = '#e3b341';
    }, 4000);
  } else if (event.event === 'TIMEOUT') {
    currentGateEl.textContent = 'EXPIRED (TIMEOUT)';
    currentGateEl.style.color = '#f85149';
    resetGateTimeout = setTimeout(() => {
      currentGateEl.textContent = 'NONE';
      currentGateEl.style.color = '#e3b341';
    }, 4000);
  } else if (event.event === 'DEVICE_DISCONNECTED') {
    currentGateEl.textContent = 'NONE';
    currentGateEl.style.color = '#e3b341';
  }

  const emptyPlaceholder = auditLogEl.querySelector('.empty-log');
  if (emptyPlaceholder) {
    emptyPlaceholder.remove();
  }

  const entry = document.createElement('div');
  entry.className = 'log-entry';

  const timeStr = event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();

  let detailsHtml = '';
  if (event.cmd) {
    detailsHtml += `<div class="cmd">Command: ${escapeHtml(event.cmd)}</div>`;
  }
  let metaInfo = [];
  if (event.rule) metaInfo.push(`Rule: ${escapeHtml(event.rule)}`);
  if (event.verdict) metaInfo.push(`Verdict: <strong>${escapeHtml(event.verdict)}</strong>`);
  if (event.request_id) metaInfo.push(`Req: ${escapeHtml(event.request_id)}`);
  if (metaInfo.length > 0) {
    detailsHtml += `<div class="details">${metaInfo.join(' | ')}</div>`;
  }

  entry.innerHTML = `
    <div>
      <span class="timestamp">[${timeStr}]</span>
      <span class="event-tag event-${escapeHtml(event.event)}">${escapeHtml(event.event)}</span>
    </div>
    ${detailsHtml}
  `;

  auditLogEl.insertBefore(entry, auditLogEl.firstChild);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

window.addEventListener('DOMContentLoaded', () => {
  connectWebSocket();
});
