const STORAGE_KEY = 'baiita-n8n-preview-v1';
const pageRoot = document.querySelector('#main-content');
const workflowCount = document.querySelector('#workflow-count');
const currentSectionLabel = document.querySelector('#current-section');
const createDialog = document.querySelector('#create-dialog');
const editorDialog = document.querySelector('#editor-dialog');
const launchDialog = document.querySelector('#launch-dialog');
const searchDialog = document.querySelector('#search-dialog');
const toastRegion = document.querySelector('#toast-region');
const fileInput = document.querySelector('#workflow-file');

const seedWorkflows = [
  {
    id: 'daily-revenue',
    name: 'Daily revenue digest',
    description: 'A crisp morning snapshot, delivered before stand-up.',
    category: 'Finance',
    active: true,
    icon: 'clock',
    tone: 'violet',
    lastRun: '8 min ago',
    runs: 126,
    successRate: '99.4%',
    duration: '2.4s',
    trigger: 'Weekdays · 8:30 AM',
    nodes: [
      { label: 'Schedule', detail: 'Weekdays · 8:30 AM', icon: 'clock', tone: 'violet' },
      { label: 'AI summary', detail: 'Turn numbers into a story', icon: 'sparkles', tone: 'mint' },
      { label: 'Slack', detail: 'Post to #daily-revenue', icon: 'workflow', tone: 'coral' },
    ],
  },
  {
    id: 'new-lead-crm',
    name: 'New lead → CRM',
    description: 'Every form submission gets enriched and routed.',
    category: 'Sales',
    active: true,
    icon: 'webhook',
    tone: 'mint',
    lastRun: '13 min ago',
    runs: 84,
    successRate: '100%',
    duration: '3.1s',
    trigger: 'On form submission',
    nodes: [
      { label: 'Form webhook', detail: 'New lead received', icon: 'webhook', tone: 'violet' },
      { label: 'Enrich contact', detail: 'Clean and qualify the lead', icon: 'sparkles', tone: 'mint' },
      { label: 'CRM + Slack', detail: 'Create a deal and notify sales', icon: 'workflow', tone: 'coral' },
    ],
  },
  {
    id: 'support-triage',
    name: 'Support ticket triage',
    description: 'Give every customer question a helpful first step.',
    category: 'Support',
    active: true,
    icon: 'sparkles',
    tone: 'coral',
    lastRun: '28 min ago',
    runs: 58,
    successRate: '98.2%',
    duration: '1.8s',
    trigger: 'When a ticket arrives',
    nodes: [
      { label: 'New ticket', detail: 'Listen for incoming support', icon: 'mail', tone: 'violet' },
      { label: 'AI triage', detail: 'Classify intent and urgency', icon: 'sparkles', tone: 'mint' },
      { label: 'Create issue', detail: 'Route to the right teammate', icon: 'workflow', tone: 'coral' },
    ],
  },
  {
    id: 'content-pipeline',
    name: 'Weekly content pipeline',
    description: 'Turn a rough idea into a ready-to-review draft.',
    category: 'Marketing',
    active: false,
    icon: 'layers',
    tone: 'blue',
    lastRun: 'Yesterday',
    runs: 21,
    successRate: '94.2%',
    duration: '5.8s',
    trigger: 'Every Monday · 9:00 AM',
    nodes: [
      { label: 'Weekly schedule', detail: 'Monday · 9:00 AM', icon: 'clock', tone: 'violet' },
      { label: 'Draft with AI', detail: 'Create a first draft', icon: 'sparkles', tone: 'mint' },
      { label: 'Review in Notion', detail: 'Send to the editorial team', icon: 'file', tone: 'coral' },
    ],
  },
  {
    id: 'order-watch',
    name: 'Order exception watcher',
    description: 'Spot unusual orders and surface them quickly.',
    category: 'Operations',
    active: true,
    icon: 'workflow',
    tone: 'blue',
    lastRun: '2 hours ago',
    runs: 143,
    successRate: '99.9%',
    duration: '1.2s',
    trigger: 'When a new order is placed',
    nodes: [
      { label: 'New order', detail: 'Watch incoming orders', icon: 'webhook', tone: 'violet' },
      { label: 'Check conditions', detail: 'Flag unusual patterns', icon: 'filter', tone: 'mint' },
      { label: 'Notify operations', detail: 'Send only exceptions', icon: 'mail', tone: 'coral' },
    ],
  },
];

const templates = [
  {
    id: 'lead-routing',
    name: 'Enrich and route every new lead',
    category: 'Sales',
    description: 'Capture a form submission, enrich the contact, and loop in the right teammate.',
    uses: '4.8k',
    trigger: 'When a webhook arrives',
    destination: 'Slack',
    icon: 'webhook',
    tone: 'violet',
    nodes: [
      { label: 'Lead webhook', detail: 'A new form submission', icon: 'webhook', tone: 'violet' },
      { label: 'Enrich lead', detail: 'Add useful context', icon: 'sparkles', tone: 'mint' },
      { label: 'Slack + CRM', detail: 'Route to your team', icon: 'workflow', tone: 'coral' },
    ],
  },
  {
    id: 'inbox-assistant',
    name: 'A calmer, smarter inbox',
    category: 'AI & support',
    description: 'Summarize incoming support email and create a tidy task for follow-up.',
    uses: '3.2k',
    trigger: 'When an app event happens',
    destination: 'Notion',
    icon: 'mail',
    tone: 'coral',
    nodes: [
      { label: 'New email', detail: 'Watch the support inbox', icon: 'mail', tone: 'violet' },
      { label: 'AI summary', detail: 'Find intent and next steps', icon: 'sparkles', tone: 'mint' },
      { label: 'Create a task', detail: 'Keep the team in sync', icon: 'file', tone: 'coral' },
    ],
  },
  {
    id: 'daily-brief',
    name: 'Your daily team briefing',
    category: 'Productivity',
    description: 'Collect the day’s updates and send one clear, friendly morning digest.',
    uses: '2.6k',
    trigger: 'On a schedule',
    destination: 'Slack',
    icon: 'clock',
    tone: 'mint',
    nodes: [
      { label: 'Morning schedule', detail: 'Every weekday', icon: 'clock', tone: 'violet' },
      { label: 'Gather updates', detail: 'Bring the context together', icon: 'layers', tone: 'mint' },
      { label: 'Post a briefing', detail: 'Share with your team', icon: 'workflow', tone: 'coral' },
    ],
  },
  {
    id: 'invoice-followup',
    name: 'Gentle invoice follow-ups',
    category: 'Finance',
    description: 'Check what is due, then send a thoughtful reminder at just the right time.',
    uses: '1.9k',
    trigger: 'On a schedule',
    destination: 'Email',
    icon: 'file',
    tone: 'blue',
    nodes: [
      { label: 'Daily check', detail: 'Look for due invoices', icon: 'clock', tone: 'violet' },
      { label: 'Find exceptions', detail: 'Skip settled invoices', icon: 'filter', tone: 'mint' },
      { label: 'Send a reminder', detail: 'Keep the tone human', icon: 'mail', tone: 'coral' },
    ],
  },
  {
    id: 'content-review',
    name: 'From idea to review-ready draft',
    category: 'Marketing',
    description: 'Turn a note into a first draft and place it in your editorial queue.',
    uses: '1.5k',
    trigger: 'When an app event happens',
    destination: 'Notion',
    icon: 'sparkles',
    tone: 'violet',
    nodes: [
      { label: 'New idea', detail: 'Pick up a fresh brief', icon: 'webhook', tone: 'violet' },
      { label: 'Draft with AI', detail: 'Make a useful starting point', icon: 'sparkles', tone: 'mint' },
      { label: 'Request review', detail: 'Create a Notion page', icon: 'file', tone: 'coral' },
    ],
  },
  {
    id: 'order-alerts',
    name: 'Only the order alerts that matter',
    category: 'Operations',
    description: 'Watch order events, spot exceptions, and nudge the right channel.',
    uses: '980',
    trigger: 'When an app event happens',
    destination: 'Slack',
    icon: 'workflow',
    tone: 'coral',
    nodes: [
      { label: 'New order', detail: 'Listen for each purchase', icon: 'webhook', tone: 'violet' },
      { label: 'Check the order', detail: 'Apply your own rules', icon: 'filter', tone: 'mint' },
      { label: 'Send an alert', detail: 'Surface exceptions only', icon: 'workflow', tone: 'coral' },
    ],
  },
];

const seedExecutions = [
  { id: 'run-1', workflowId: 'daily-revenue', name: 'Daily revenue digest', status: 'success', when: '2 min ago', duration: '2.4s', trigger: 'Schedule trigger' },
  { id: 'run-2', workflowId: 'support-triage', name: 'Support ticket triage', status: 'success', when: '11 min ago', duration: '1.8s', trigger: 'App event' },
  { id: 'run-3', workflowId: 'new-lead-crm', name: 'New lead → CRM', status: 'success', when: '24 min ago', duration: '3.1s', trigger: 'Webhook' },
  { id: 'run-4', workflowId: 'content-pipeline', name: 'Weekly content pipeline', status: 'failed', when: '1 hour ago', duration: '5.8s', trigger: 'Schedule trigger' },
  { id: 'run-5', workflowId: 'order-watch', name: 'Order exception watcher', status: 'success', when: '2 hours ago', duration: '1.2s', trigger: 'App event' },
];

const pageTitles = {
  overview: 'Overview',
  workflows: 'Workflows',
  templates: 'Templates',
  executions: 'Executions',
  credentials: 'Credentials',
  settings: 'Settings',
};

let pendingTemplate = null;
let activeEditorId = null;
let selectedSearchResult = 0;
let toastId = 0;
let flowFilter = 'All';
let flowQuery = '';
let state = loadState();

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null');
    if (saved && Array.isArray(saved.workflows) && Array.isArray(saved.executions)) {
      return {
        workflows: saved.workflows.filter((flow) => flow && typeof flow.id === 'string' && typeof flow.name === 'string'),
        executions: saved.executions.filter((run) => run && typeof run.name === 'string'),
        extraRuns: Number.isFinite(saved.extraRuns) ? saved.extraRuns : 0,
      };
    }
  } catch {
    // If local preview storage is unavailable or damaged, start with fresh demo data.
  }
  return { workflows: structuredClone(seedWorkflows), executions: structuredClone(seedExecutions), extraRuns: 0 };
}

function saveState() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      workflows: state.workflows,
      executions: state.executions.slice(0, 40),
      extraRuns: state.extraRuns,
    }));
  } catch {
    showToast('Your browser could not save this preview. Changes may not persist.', 'error');
  }
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (character) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[character]);
}

function icon(name, className = 'icon') {
  const safeName = /^[a-z-]+$/.test(name) ? name : 'workflow';
  return `<svg class="${className}" aria-hidden="true"><use href="/assets/icons.svg#${safeName}"></use></svg>`;
}

function getWorkflow(id) {
  return state.workflows.find((flow) => flow.id === id);
}

function appBadge(iconName, tone = 'violet', extraClass = '') {
  return `<span class="workflow-app-icon tone-${escapeHtml(tone)} ${extraClass}">${icon(iconName)}</span>`;
}

function formatNumber(number) {
  return new Intl.NumberFormat('en-US').format(number);
}

function todayLabel() {
  return new Intl.DateTimeFormat('en', { weekday: 'long', month: 'short', day: 'numeric' }).format(new Date());
}

function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  const id = ++toastId;
  toast.className = `toast${type === 'error' ? ' error' : ''}`;
  toast.dataset.toastId = String(id);
  toast.innerHTML = `<span class="toast-mark">${icon(type === 'error' ? 'close' : 'check')}</span><span>${escapeHtml(message)}</span>`;
  toastRegion.append(toast);
  window.setTimeout(() => {
    const item = toastRegion.querySelector(`[data-toast-id="${id}"]`);
    item?.remove();
  }, 3500);
}

function renderOverview() {
  const activeCount = state.workflows.filter((flow) => flow.active).length;
  const executionCount = 2481 + state.extraRuns;
  const workflows = state.workflows.slice(0, 4);
  const recentRuns = state.executions.slice(0, 4);
  const date = escapeHtml(todayLabel());

  return `
    <section class="page-heading">
      <div class="page-heading-copy">
        <div class="eyebrow"><span class="eyebrow-dot"></span>${date}<span class="eyebrow-separator">·</span><span class="preview-pill">${icon('sparkle')} Interactive preview</span></div>
        <h1>Work smarter. <span class="gradient-text">Flow beautifully.</span></h1>
        <p>A little automation goes a long way. Make space for the work that needs you.</p>
      </div>
      <div class="page-actions">
        <button class="button-secondary" type="button" data-action="import-workflow">${icon('file')} Import JSON</button>
        <button class="button-primary" type="button" data-action="new-workflow">${icon('plus')} New workflow</button>
      </div>
    </section>

    <section class="hero-panel" aria-label="Workflow automation introduction">
      <div class="hero-copy">
        <span class="hero-kicker">${icon('sparkles')} YOUR WORKFLOWS, IN MOTION</span>
        <h2>Every little task,<br /><span>running on autopilot.</span></h2>
        <p>Connect your favorite tools, add a little logic, and let a good idea do its thing.</p>
        <div class="hero-copy-bottom">
          <button class="button-primary" type="button" data-action="browse-templates">Find your first flow ${icon('arrow-right')}</button>
          <span class="avatar-stack" aria-hidden="true"><span>B</span><span>n</span><span>+</span></span>
          <span class="hero-proof">Built to grow with you</span>
        </div>
      </div>
      <div class="hero-visual">
        <div class="workflow-preview" role="img" aria-label="A sample workflow connecting a schedule, an AI agent, and Slack">
          <div class="preview-toolbar">
            <div class="preview-workflow-name"><span class="tiny-flow-icon">${icon('workflow')}</span>Daily revenue digest</div>
            <div class="preview-toolbar-actions" aria-hidden="true"><i></i><i></i><i></i></div>
          </div>
          <div class="graph-canvas">
            <svg class="graph-wires" viewBox="0 0 500 156" preserveAspectRatio="none" aria-hidden="true">
              <path class="wire-glow" d="M110 77 C162 77 174 43 225 43 S304 43 337 57 C365 69 370 103 407 111" />
              <path d="M110 77 C162 77 174 43 225 43 S304 43 337 57 C365 69 370 103 407 111" />
              <circle cx="110" cy="77" r="3"/><circle cx="225" cy="43" r="3"/><circle cx="407" cy="111" r="3"/>
            </svg>
            <div class="flow-node node-trigger"><span class="node-icon tone-violet">${icon('clock')}</span><span><strong>Schedule</strong><small>Weekdays · 8:30</small></span><span class="node-success">${icon('check')}</span></div>
            <div class="flow-node node-agent"><span class="node-icon tone-mint">${icon('sparkles')}</span><span><strong>AI summary</strong><small>Turn data into a story</small></span><span class="node-success">${icon('check')}</span></div>
            <div class="flow-node node-slack"><span class="node-icon tone-coral">${icon('workflow')}</span><span><strong>Slack</strong><small>Post to #daily-revenue</small></span><span class="node-success">${icon('check')}</span></div>
          </div>
          <div class="preview-bottom"><span><span class="status-pulse"></span> Sample flow · 3 steps</span><span class="preview-link">A tiny idea, on repeat ↗</span></div>
        </div>
      </div>
    </section>

    <div class="section-heading">
      <div><h2>A little momentum</h2><p>A snapshot of this example workspace.</p></div>
      <span class="sample-label">${icon('sparkles')} Sample data</span>
    </div>
    <section class="metrics-grid" aria-label="Sample workspace metrics">
      <article class="metric-card"><div class="metric-top"><span class="metric-label">Active workflows</span><span class="metric-icon violet">${icon('workflow')}</span></div><div class="metric-value-row"><span class="metric-value">${activeCount}</span><span class="metric-unit">of ${state.workflows.length} flows</span></div><div class="metric-trend">${icon('trend')} Ready to run</div><svg class="metric-mini-chart" viewBox="0 0 56 24" aria-hidden="true"><path d="M2 19 11 16 18 18 27 10 34 13 42 7 54 4"/></svg></article>
      <article class="metric-card"><div class="metric-top"><span class="metric-label">Executions today</span><span class="metric-icon mint">${icon('lightning')}</span></div><div class="metric-value-row"><span class="metric-value">${formatNumber(executionCount)}</span><span class="metric-unit">sample runs</span></div><div class="metric-trend">${icon('trend')} Your flows are moving</div><svg class="metric-mini-chart mint-chart" viewBox="0 0 56 24" aria-hidden="true"><path d="M2 17 10 17 17 11 25 14 33 7 41 9 54 3"/></svg></article>
      <article class="metric-card"><div class="metric-top"><span class="metric-label">Success rate</span><span class="metric-icon coral">${icon('check')}</span></div><div class="metric-value-row"><span class="metric-value">98.6%</span><span class="metric-unit">sample average</span></div><div class="metric-trend">${icon('trend')} Smooth sailing</div><svg class="metric-mini-chart coral-chart" viewBox="0 0 56 24" aria-hidden="true"><path d="M2 16 10 14 18 15 25 10 33 12 41 6 54 5"/></svg></article>
      <article class="metric-card"><div class="metric-top"><span class="metric-label">Time given back</span><span class="metric-icon blue">${icon('clock')}</span></div><div class="metric-value-row"><span class="metric-value">42.5</span><span class="metric-unit">hrs · estimate</span></div><div class="metric-trend muted">Across this sample team</div><svg class="metric-mini-chart blue-chart" viewBox="0 0 56 24" aria-hidden="true"><path d="M2 20 10 15 17 17 25 11 33 13 41 6 54 3"/></svg></article>
    </section>

    <section class="dashboard-grid" aria-label="Workflow activity">
      <article class="panel">
        <header class="panel-header"><div class="panel-title"><h2>Recent workflows</h2><small>${state.workflows.length} in your space</small></div><button class="text-link" type="button" data-nav="workflows">View all ${icon('arrow-right')}</button></header>
        <div class="workflow-list">${workflows.length ? workflows.map(renderRecentWorkflow).join('') : renderEmptyWorkflows()}</div>
      </article>
      <article class="panel activity-panel">
        <header class="panel-header"><div class="panel-title"><h2>Just happened</h2><small>Sample activity</small></div><button class="small-icon-button" type="button" data-nav="executions" aria-label="View all executions">${icon('arrow-up-right')}</button></header>
        <div class="activity-list">${recentRuns.length ? recentRuns.map(renderActivityItem).join('') : '<div class="empty-state"><p>No runs yet. Try a sample workflow.</p></div>'}</div>
      </article>
    </section>`;
}

function renderRecentWorkflow(flow) {
  const status = flow.active ? 'Active' : 'Paused';
  return `<div class="workflow-row">
    <button class="workflow-row-main" type="button" data-open-flow="${escapeHtml(flow.id)}" aria-label="Open ${escapeHtml(flow.name)}">
      ${appBadge(flow.icon ?? 'workflow', flow.tone ?? 'violet')}
      <span class="workflow-row-info"><strong>${escapeHtml(flow.name)}</strong><small>${escapeHtml(flow.description || flow.category || 'Workflow preview')}</small></span>
    </button>
    <span class="workflow-row-time">${escapeHtml(flow.lastRun || 'Never')}</span>
    <span class="row-run-count">${formatNumber(flow.runs || 0)}<small>runs</small></span>
    <button class="workflow-toggle status-chip${flow.active ? '' : ' is-paused'}" type="button" data-action="toggle-flow" data-flow-id="${escapeHtml(flow.id)}" aria-label="${flow.active ? 'Pause' : 'Activate'} ${escapeHtml(flow.name)}">${status}</button>
  </div>`;
}

function renderActivityItem(run) {
  const failed = run.status === 'failed';
  return `<div class="activity-item">
    <span class="activity-mark${failed ? ' failed' : ''}">${icon(failed ? 'close' : 'check')}</span>
    <span class="activity-copy"><strong>${escapeHtml(run.name)}</strong><small>${failed ? 'Needs a look' : 'Completed successfully'} · ${escapeHtml(run.duration || '—')}</small></span>
    <span class="activity-time">${escapeHtml(run.when || 'Just now')}</span>
  </div>`;
}

function renderEmptyWorkflows() {
  return `<div class="empty-state"><span class="metric-icon violet">${icon('workflow')}</span><h3>Your next idea starts here.</h3><p>Create a workflow preview or pick a template to see what an automated day could look like.</p><button class="button-primary" type="button" data-action="new-workflow">${icon('plus')} New workflow</button></div>`;
}

function renderWorkflowsView() {
  const filters = ['All', 'Active', 'Paused'];
  const matching = state.workflows.filter((flow) => {
    const filterMatch = flowFilter === 'All' || (flowFilter === 'Active' ? flow.active : !flow.active);
    const queryMatch = `${flow.name} ${flow.category ?? ''} ${flow.description ?? ''}`.toLowerCase().includes(flowQuery.toLowerCase());
    return filterMatch && queryMatch;
  });
  return `
    <section class="view-title-row"><div><div class="eyebrow"><span class="eyebrow-dot"></span>THE WORK BEHIND THE MAGIC</div><h1>Your workflows</h1><p>Little building blocks, working together in a bigger way.</p></div><div class="view-title-actions"><button class="button-secondary" type="button" data-action="import-workflow">${icon('file')} Import JSON</button><button class="button-primary" type="button" data-action="new-workflow">${icon('plus')} New workflow</button></div></section>
    <div class="view-toolbar"><div class="filter-tabs" role="tablist" aria-label="Filter workflows">${filters.map((filter) => `<button class="filter-tab${flowFilter === filter ? ' is-active' : ''}" type="button" role="tab" aria-selected="${flowFilter === filter}" data-flow-filter="${filter}">${filter}<span>${filter === 'All' ? state.workflows.length : filter === 'Active' ? state.workflows.filter((flow) => flow.active).length : state.workflows.filter((flow) => !flow.active).length}</span></button>`).join('')}</div><label class="view-search">${icon('search')}<span class="sr-only">Filter workflows</span><input id="workflow-query" type="search" placeholder="Find a workflow..." value="${escapeHtml(flowQuery)}" autocomplete="off" /></label></div>
    <section class="workflows-table" aria-label="Workflows list">
      <div class="table-head"><span>Workflow</span><span>Last run</span><span>Runs</span><span>Status</span><span></span></div>
      ${matching.length ? matching.map(renderWorkflowTableRow).join('') : `<div class="empty-state"><span class="metric-icon violet">${icon('search')}</span><h3>No workflows found</h3><p>Try another search, change your filter, or create a new workflow preview.</p><button class="button-quiet" type="button" data-action="clear-workflow-search">Clear filters</button></div>`}
    </section>
    <div class="section-heading"><div><h2>Need a spark?</h2><p>Start with a template, then make it yours.</p></div><button class="text-link" type="button" data-nav="templates">Explore templates ${icon('arrow-right')}</button></div>`;
}

function renderWorkflowTableRow(flow) {
  return `<div class="table-row">
    <div class="table-flow"><button class="workflow-row-main" type="button" data-open-flow="${escapeHtml(flow.id)}" aria-label="Open ${escapeHtml(flow.name)}">${appBadge(flow.icon ?? 'workflow', flow.tone ?? 'violet')}<span class="table-flow-copy"><strong>${escapeHtml(flow.name)}</strong><small>${escapeHtml(flow.description || flow.category || 'Workflow preview')}</small></span></button></div>
    <span class="table-cell-muted">${escapeHtml(flow.lastRun || 'Never')}</span>
    <span class="table-cell-muted">${formatNumber(flow.runs || 0)} runs</span>
    <button class="workflow-toggle status-chip workflow-table-status${flow.active ? '' : ' is-paused'}" type="button" data-action="toggle-flow" data-flow-id="${escapeHtml(flow.id)}">${flow.active ? 'Active' : 'Paused'}</button>
    <div class="table-row-actions"><button class="small-icon-button" type="button" data-action="run-flow" data-flow-id="${escapeHtml(flow.id)}" aria-label="Run ${escapeHtml(flow.name)}">${icon('play')}</button><button class="small-icon-button" type="button" data-open-flow="${escapeHtml(flow.id)}" aria-label="Edit ${escapeHtml(flow.name)}">${icon('arrow-up-right')}</button></div>
  </div>`;
}

function renderTemplateCard(template) {
  const icons = template.nodes.slice(0, 3).map((node) => appBadge(node.icon, node.tone)).join('');
  return `<article class="template-card">
    <div class="template-card-top"><div class="template-icon-group">${icons}</div><span class="template-category">${escapeHtml(template.category)}</span></div>
    <h3>${escapeHtml(template.name)}</h3><p>${escapeHtml(template.description)}</p>
    <div class="template-card-bottom"><span class="template-uses">${icon('workflow')}${escapeHtml(template.uses)} uses</span><button class="template-use-button" type="button" data-use-template="${escapeHtml(template.id)}">Use this idea ${icon('arrow-right')}</button></div>
  </article>`;
}

function renderTemplatesView() {
  return `
    <section class="view-title-row"><div><div class="eyebrow"><span class="eyebrow-dot"></span>GOOD IDEAS, READY TO GO</div><h1>Borrow a little brilliance.</h1><p>Pick a starting point. Every workflow can be changed to fit your world.</p></div><div class="view-title-actions"><button class="button-primary" type="button" data-action="new-workflow">${icon('plus')} Start from scratch</button></div></section>
    <section class="template-banner"><div class="template-banner-copy"><span class="hero-kicker">${icon('sparkles')} CURATED FOR YOUR NEXT IDEA</span><h2>Start small. Make something surprisingly useful.</h2><p>These are interactive previews — your real n8n workflows stay in your own instance.</p></div><div class="template-banner-graphic" aria-hidden="true"><span>${icon('webhook')}</span>${icon('arrow-right')}<span>${icon('sparkles')}</span>${icon('arrow-right')}<span>${icon('workflow')}</span></div></section>
    <section class="template-grid" aria-label="Workflow ideas">${templates.map(renderTemplateCard).join('')}</section>`;
}

function renderExecutionsView() {
  return `
    <section class="view-title-row"><div><div class="eyebrow"><span class="eyebrow-dot"></span>THE PAPER TRAIL</div><h1>Executions</h1><p>Every run leaves a breadcrumb. Here's a handful from the demo workspace.</p></div><div class="view-title-actions"><span class="sample-label">${icon('sparkles')} Sample activity</span></div></section>
    <div class="info-banner">${icon('sparkles')}<div><strong>These runs are illustrative.</strong><p>Running a workflow here plays a local simulation; production executions and logs live in your self-hosted n8n editor.</p></div></div>
    <section class="execution-list executions-table" aria-label="Recent execution history">
      <div class="execution-head"><span>Workflow</span><span>Trigger</span><span>Started</span><span>Status</span><span>Duration</span></div>
      ${state.executions.length ? state.executions.slice(0, 30).map((run) => `<div class="execution-row"><span class="execution-flow"><span class="activity-mark${run.status === 'failed' ? ' failed' : ''}">${icon(run.status === 'failed' ? 'close' : 'check')}</span><strong>${escapeHtml(run.name)}</strong></span><span class="table-cell-muted">${escapeHtml(run.trigger || 'Manual')}</span><span class="table-cell-muted">${escapeHtml(run.when || 'Just now')}</span><span class="execution-status${run.status === 'failed' ? ' failed' : ''}">${icon(run.status === 'failed' ? 'close' : 'check')}${run.status === 'failed' ? 'Failed' : 'Success'}</span><span class="table-cell-muted">${escapeHtml(run.duration || '—')}</span></div>`).join('') : `<div class="empty-state"><span class="metric-icon mint">${icon('clock')}</span><h3>No runs yet</h3><p>Open a workflow preview and try a simulation.</p><button class="button-primary" type="button" data-nav="workflows">Explore workflows ${icon('arrow-right')}</button></div>`}
    </section>`;
}

function renderCredentialsView() {
  return `
    <section class="view-title-row"><div><div class="eyebrow"><span class="eyebrow-dot"></span>CONNECT WITH CARE</div><h1>Credentials</h1><p>Keep your keys close, and your secrets even closer.</p></div></section>
    <div class="info-banner">${icon('shield')}<div><strong>This preview never asks for or stores credentials.</strong><p>Connect apps securely in your own n8n instance. Credentials stay encrypted in that instance's database and settings volume.</p></div></div>
    <div class="credentials-grid"><section class="credential-card"><h2>Connections in your real instance</h2><p>Once the Docker stack is running, open the n8n editor to add and manage your app credentials.</p><div class="credential-placeholder"><span class="metric-icon violet">${icon('key')}</span><span><strong>No credentials are connected to this demo</strong><small>Live credentials are managed in your n8n editor.</small></span></div><button class="button-secondary" type="button" data-action="launch-editor">${icon('arrow-up-right')} Setup your editor</button></section>
    <aside class="credential-aside"><h2>A few good habits</h2><p>Small security choices make a big difference.</p><ul class="permission-list"><li>${icon('check')}Use a different credential per environment.</li><li>${icon('check')}Rotate keys when someone leaves your team.</li><li>${icon('check')}Use HTTPS before exposing n8n publicly.</li><li>${icon('check')}Never commit your <code>.env</code> file or secrets.</li></ul></aside></div>`;
}

function renderSettingsView() {
  return `
    <section class="view-title-row"><div><div class="eyebrow"><span class="eyebrow-dot"></span>MAKE IT YOURS</div><h1>Settings</h1><p>A few details about this local, interactive preview.</p></div></section>
    <div class="settings-grid"><section class="settings-card"><h2>Workspace preferences</h2><div class="setting-row"><span><strong>Workspace name</strong><small>Shown in the navigation and activity view.</small></span><span class="setting-control">Baiita Studio</span></div><div class="setting-row"><span><strong>Preview mode</strong><small>Workflow actions are simulated in your browser.</small></span><span class="setting-control">Enabled</span></div><div class="setting-row"><span><strong>Saved on this device</strong><small>Preview flows use local browser storage.</small></span><span class="setting-control">${state.workflows.length} workflows</span></div></section>
    <section class="settings-card"><h2>Reset the preview</h2><div class="setting-row"><span><strong>Restore the sample workspace</strong><small>Remove locally created preview flows and return to the original examples.</small></span></div><button class="button-secondary" type="button" data-action="reset-demo">${icon('refresh')} Reset demo data</button></section></div>
    <div class="info-banner settings-info-banner">${icon('file')}<div><strong>Want to change the real n8n settings?</strong><p>Use the Docker Compose environment variables and the n8n editor. This screen only changes the browser-based demo.</p></div></div>`;
}

function renderCurrentView({ focusHeading = false } = {}) {
  const current = pageTitles[state.section] ? state.section : 'overview';
  state.section = current;
  currentSectionLabel.textContent = pageTitles[current];
  workflowCount.textContent = String(state.workflows.length);
  document.querySelectorAll('[data-nav]').forEach((button) => {
    const selected = button.dataset.nav === current;
    button.classList.toggle('is-active', selected);
    if (selected && button.classList.contains('nav-item')) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  });
  const view = {
    overview: renderOverview,
    workflows: renderWorkflowsView,
    templates: renderTemplatesView,
    executions: renderExecutionsView,
    credentials: renderCredentialsView,
    settings: renderSettingsView,
  }[current];
  pageRoot.innerHTML = view();
  if (focusHeading) pageRoot.querySelector('h1')?.focus({ preventScroll: true });
}

function newId() {
  return globalThis.crypto?.randomUUID?.() ?? `flow-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function openDialog(dialog) {
  if (!dialog.open) dialog.showModal();
}

function openCreateDialog(template = null) {
  pendingTemplate = template;
  const form = document.querySelector('#workflow-form');
  form.reset();
  const name = document.querySelector('#workflow-name');
  if (template) {
    name.value = template.name;
    document.querySelector('#workflow-trigger').value = template.trigger;
    const destinations = [...document.querySelector('#workflow-destination').options];
    if (destinations.some((option) => option.value === template.destination)) {
      document.querySelector('#workflow-destination').value = template.destination;
    }
  }
  openDialog(createDialog);
  window.setTimeout(() => name.focus(), 30);
}

function nodeFor(trigger, destination) {
  const triggerIcon = trigger.toLowerCase().includes('schedule') ? 'clock' : trigger.toLowerCase().includes('webhook') ? 'webhook' : 'lightning';
  const lastIcon = destination.toLowerCase().includes('email') ? 'mail' : destination.toLowerCase().includes('notion') ? 'file' : 'workflow';
  return [
    { label: trigger.replace(/^When /, '').replace(/^On /, ''), detail: 'Start the workflow', icon: triggerIcon, tone: 'violet' },
    { label: 'Shape the data', detail: 'Add your own logic', icon: 'sparkles', tone: 'mint' },
    { label: destination, detail: 'Send the useful part along', icon: lastIcon, tone: 'coral' },
  ];
}

function createWorkflowFromForm(event) {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const name = String(formData.get('name') ?? '').trim();
  if (!name) {
    document.querySelector('#workflow-name').focus();
    return;
  }
  const trigger = String(formData.get('trigger') ?? 'Manually');
  const destination = String(formData.get('destination') ?? 'Slack');
  const template = pendingTemplate;
  const flow = {
    id: newId(),
    name: name.slice(0, 80),
    description: template?.description ?? `${trigger} · ${destination}`,
    category: template?.category ?? 'My workflow',
    active: false,
    icon: template?.icon ?? 'workflow',
    tone: template?.tone ?? 'violet',
    lastRun: 'Never',
    runs: 0,
    successRate: '—',
    duration: '—',
    trigger,
    nodes: template ? structuredClone(template.nodes) : nodeFor(trigger, destination),
  };
  pendingTemplate = null;
  state.workflows.unshift(flow);
  state.section = 'workflows';
  saveState();
  renderCurrentView();
  createDialog.close();
  showToast('Workflow preview created. Shape the steps or try a simulation.');
  openEditor(flow.id);
}

function renderEditor(flow) {
  const nodes = Array.isArray(flow.nodes) && flow.nodes.length ? flow.nodes : nodeFor(flow.trigger || 'When you start', 'Slack');
  const visibleNodes = nodes.slice(0, 5);
  const middle = visibleNodes.map((node, index) => `${index ? '<span class="editor-connector" aria-hidden="true"></span>' : ''}<div class="editor-node"><span class="node-icon tone-${escapeHtml(node.tone || 'violet')}">${icon(node.icon || 'workflow')}</span><span><strong>${escapeHtml(node.label)}</strong><small>${escapeHtml(node.detail || 'Workflow step')}</small></span></div>`).join('');
  const safeId = escapeHtml(flow.id);
  return `<header class="editor-header"><div class="editor-title-group">${appBadge(flow.icon || 'workflow', flow.tone || 'violet')}<span><h2 id="editor-title">${escapeHtml(flow.name)}</h2><small>${flow.active ? 'Active in this demo' : 'Draft preview'} · ${escapeHtml(flow.category || 'Workflow')}</small></span></div><div class="editor-actions"><button class="button-secondary" type="button" data-action="toggle-flow" data-flow-id="${safeId}">${icon(flow.active ? 'pause' : 'play')}${flow.active ? 'Pause' : 'Activate'}</button><button class="button-primary" type="button" data-action="run-flow" data-flow-id="${safeId}">${icon('play')} Run simulation</button><button class="dialog-close" type="button" data-action="close-dialog" aria-label="Close workflow preview">${icon('close')}</button></div></header><div class="editor-canvas" role="img" aria-label="${escapeHtml(flow.name)} workflow preview with ${visibleNodes.length} steps"><div class="editor-flow">${middle}</div></div><footer class="editor-caption"><span><span class="status-pulse"></span>Browser-only simulation · not connected to app credentials</span><span>${visibleNodes.length} visible steps · ${flow.runs ? `${formatNumber(flow.runs)} sample runs` : 'No runs yet'}</span></footer>`;
}

function openEditor(id) {
  const flow = getWorkflow(id);
  if (!flow) return;
  activeEditorId = id;
  document.querySelector('#editor-card').innerHTML = renderEditor(flow);
  openDialog(editorDialog);
}

function refreshEditorIfOpen() {
  if (!editorDialog.open || !activeEditorId) return;
  const flow = getWorkflow(activeEditorId);
  if (flow) document.querySelector('#editor-card').innerHTML = renderEditor(flow);
  else editorDialog.close();
}

function toggleWorkflow(id) {
  const flow = getWorkflow(id);
  if (!flow) return;
  flow.active = !flow.active;
  saveState();
  renderCurrentView();
  refreshEditorIfOpen();
  showToast(`${flow.name} is ${flow.active ? 'active in the demo' : 'paused in the demo'}.`);
}

function runWorkflow(id, button) {
  const flow = getWorkflow(id);
  if (!flow || button?.dataset.running === 'true') return;
  if (button) {
    button.dataset.running = 'true';
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    button.innerHTML = `${icon('refresh')} Running…`;
  }
  window.setTimeout(() => {
    const run = {
      id: newId(),
      workflowId: flow.id,
      name: flow.name,
      status: 'success',
      when: 'Just now',
      duration: '1.6s',
      trigger: 'Manual simulation',
    };
    flow.runs = (flow.runs || 0) + 1;
    flow.lastRun = 'Just now';
    state.extraRuns += 1;
    state.executions.unshift(run);
    state.executions = state.executions.slice(0, 40);
    saveState();
    renderCurrentView();
    refreshEditorIfOpen();
    showToast(`Simulation complete — ${flow.name} is looking good.`);
  }, 850);
}

function openSearch() {
  openDialog(searchDialog);
  selectedSearchResult = 0;
  const input = document.querySelector('#global-search');
  input.value = '';
  renderSearchResults('');
  window.setTimeout(() => input.focus(), 20);
}

function renderSearchResults(query) {
  const results = document.querySelector('#search-results');
  const normalized = query.trim().toLowerCase();
  const matchingFlows = state.workflows.filter((flow) => `${flow.name} ${flow.category ?? ''}`.toLowerCase().includes(normalized)).slice(0, 5);
  const matchingTemplates = templates.filter((template) => `${template.name} ${template.category} ${template.description}`.toLowerCase().includes(normalized)).slice(0, 4);
  const pages = Object.entries(pageTitles).filter(([key, title]) => key !== 'overview' && title.toLowerCase().includes(normalized));
  const hasResults = matchingFlows.length || matchingTemplates.length || pages.length;
  if (!hasResults) {
    results.innerHTML = '<div class="search-empty">Nothing found. Try “lead”, “support”, or “templates”.</div>';
    selectedSearchResult = 0;
    return;
  }
  let html = '';
  if (matchingFlows.length) {
    html += `<p class="search-section-label">Workflows</p>${matchingFlows.map((flow) => `<button class="search-result" type="button" data-search-flow="${escapeHtml(flow.id)}">${appBadge(flow.icon || 'workflow', flow.tone || 'violet')}<span class="search-result-copy"><strong>${escapeHtml(flow.name)}</strong><small>${escapeHtml(flow.category || 'Workflow')} · ${flow.active ? 'Active' : 'Paused'}</small></span>${icon('arrow-up-right')}</button>`).join('')}`;
  }
  if (matchingTemplates.length) {
    html += `<p class="search-section-label">Ideas</p>${matchingTemplates.map((template) => `<button class="search-result" type="button" data-search-template="${escapeHtml(template.id)}">${appBadge(template.icon, template.tone)}<span class="search-result-copy"><strong>${escapeHtml(template.name)}</strong><small>${escapeHtml(template.category)} template</small></span>${icon('arrow-right')}</button>`).join('')}`;
  }
  if (pages.length) {
    html += `<p class="search-section-label">Workspace</p>${pages.map(([key, title]) => `<button class="search-result" type="button" data-search-view="${escapeHtml(key)}">${appBadge(key === 'executions' ? 'clock' : key === 'credentials' ? 'key' : key === 'settings' ? 'settings' : 'layers', 'blue')}<span class="search-result-copy"><strong>${escapeHtml(title)}</strong><small>Workspace page</small></span>${icon('arrow-up-right')}</button>`).join('')}`;
  }
  results.innerHTML = html;
  const rows = results.querySelectorAll('.search-result');
  rows.forEach((row, index) => row.classList.toggle('is-selected', index === selectedSearchResult));
}

function activateSearchResult(result) {
  if (!result) return;
  const flowId = result.dataset.searchFlow;
  const templateId = result.dataset.searchTemplate;
  const view = result.dataset.searchView;
  searchDialog.close();
  if (flowId) openEditor(flowId);
  else if (templateId) {
    state.section = 'templates';
    renderCurrentView();
    openCreateDialog(templates.find((template) => template.id === templateId));
  } else if (view && pageTitles[view]) {
    state.section = view;
    renderCurrentView();
  }
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    showToast('Copied to clipboard.');
  } catch {
    const temporary = document.createElement('textarea');
    temporary.value = text;
    temporary.setAttribute('readonly', '');
    temporary.className = 'clipboard-helper';
    document.body.append(temporary);
    temporary.select();
    const copied = document.execCommand('copy');
    temporary.remove();
    showToast(copied ? 'Copied to clipboard.' : 'Copy was blocked by your browser.', copied ? 'success' : 'error');
  }
}

function importWorkflowFile(file) {
  if (!file) return;
  if (file.size > 2 * 1024 * 1024) {
    showToast('That JSON file is larger than 2 MB. Try a smaller export.', 'error');
    return;
  }
  const reader = new FileReader();
  reader.addEventListener('load', () => {
    try {
      const parsed = JSON.parse(String(reader.result ?? ''));
      if (!parsed || typeof parsed !== 'object' || !Array.isArray(parsed.nodes)) {
        throw new Error('This does not look like an n8n workflow export.');
      }
      const importedNodes = parsed.nodes.slice(0, 5).map((node, index) => {
        const label = typeof node?.name === 'string' ? node.name.slice(0, 56) : `Imported step ${index + 1}`;
        const type = typeof node?.type === 'string' ? node.type.toLowerCase() : '';
        const nodeIcon = type.includes('trigger') || type.includes('webhook') ? 'webhook' : type.includes('ai') || type.includes('agent') ? 'sparkles' : 'workflow';
        return { label, detail: 'Imported step preview', icon: nodeIcon, tone: ['violet', 'mint', 'coral'][index % 3] };
      });
      if (!importedNodes.length) throw new Error('This workflow does not contain any nodes.');
      const flow = {
        id: newId(),
        name: (typeof parsed.name === 'string' && parsed.name.trim() ? parsed.name.trim() : file.name.replace(/\.json$/i, '')).slice(0, 80),
        description: `Imported preview · ${parsed.nodes.length} step${parsed.nodes.length === 1 ? '' : 's'}`,
        category: 'Imported JSON',
        active: false,
        icon: 'file',
        tone: 'blue',
        lastRun: 'Never',
        runs: 0,
        successRate: '—',
        duration: '—',
        trigger: 'Imported from JSON',
        nodes: importedNodes,
      };
      state.workflows.unshift(flow);
      state.section = 'workflows';
      saveState();
      renderCurrentView();
      openEditor(flow.id);
      showToast('Imported a safe preview. Credentials and executable settings were not imported.');
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Could not read that workflow JSON.', 'error');
    }
  });
  reader.addEventListener('error', () => showToast('Could not read that file.', 'error'));
  reader.readAsText(file);
}

function useTemplate(id) {
  const template = templates.find((item) => item.id === id);
  if (!template) return;
  openCreateDialog(template);
}

function resetDemo() {
  const confirmed = window.confirm('Reset this browser preview to the original sample workflows? Locally created demo flows and runs will be removed.');
  if (!confirmed) return;
  state = { workflows: structuredClone(seedWorkflows), executions: structuredClone(seedExecutions), extraRuns: 0 };
  flowFilter = 'All';
  flowQuery = '';
  saveState();
  renderCurrentView();
  showToast('The sample workspace is back to its starting point.');
}

function handleAction(button) {
  const action = button.dataset.action;
  switch (action) {
    case 'new-workflow': openCreateDialog(); break;
    case 'browse-templates':
      state.section = 'templates';
      renderCurrentView();
      break;
    case 'import-workflow': fileInput.click(); break;
    case 'launch-editor': openDialog(launchDialog); break;
    case 'open-search': openSearch(); break;
    case 'toggle-sidebar': document.querySelector('#sidebar').classList.toggle('is-open'); break;
    case 'toggle-flow': toggleWorkflow(button.dataset.flowId); break;
    case 'run-flow': runWorkflow(button.dataset.flowId, button); break;
    case 'close-dialog':
      button.closest('dialog')?.close();
      if (button.closest('#editor-dialog')) activeEditorId = null;
      break;
    case 'copy-command': copyText('docker compose up --build -d'); break;
    case 'copy-url': copyText('http://localhost:5678'); break;
    case 'reset-demo': resetDemo(); break;
    case 'clear-workflow-search': flowFilter = 'All'; flowQuery = ''; renderCurrentView(); break;
    case 'profile': showToast('Workspace profile settings are available in your n8n editor.'); break;
    default: break;
  }
}

document.addEventListener('click', (event) => {
  const nav = event.target.closest('[data-nav]');
  if (nav) {
    state.section = nav.dataset.nav;
    flowFilter = 'All';
    flowQuery = '';
    renderCurrentView();
    document.querySelector('#sidebar').classList.remove('is-open');
    return;
  }

  const filter = event.target.closest('[data-flow-filter]');
  if (filter) {
    flowFilter = filter.dataset.flowFilter;
    renderCurrentView();
    return;
  }

  const flowOpen = event.target.closest('[data-open-flow]');
  if (flowOpen) {
    openEditor(flowOpen.dataset.openFlow);
    return;
  }

  const templateButton = event.target.closest('[data-use-template]');
  if (templateButton) {
    useTemplate(templateButton.dataset.useTemplate);
    return;
  }

  const searchResult = event.target.closest('[data-search-flow], [data-search-template], [data-search-view]');
  if (searchResult) {
    activateSearchResult(searchResult);
    return;
  }

  const actionButton = event.target.closest('[data-action]');
  if (actionButton) handleAction(actionButton);
});

document.querySelector('#workflow-form').addEventListener('submit', createWorkflowFromForm);
document.querySelector('#global-search').addEventListener('input', (event) => {
  selectedSearchResult = 0;
  renderSearchResults(event.target.value);
});
pageRoot.addEventListener('input', (event) => {
  if (event.target.id !== 'workflow-query') return;
  flowQuery = event.target.value;
  const position = event.target.selectionStart;
  renderCurrentView();
  const input = document.querySelector('#workflow-query');
  input.focus();
  input.setSelectionRange(position, position);
});
fileInput.addEventListener('change', (event) => {
  importWorkflowFile(event.target.files?.[0]);
  event.target.value = '';
});

for (const dialog of [createDialog, editorDialog, launchDialog, searchDialog]) {
  dialog.addEventListener('click', (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener('close', () => {
    if (dialog === editorDialog) activeEditorId = null;
  });
}

searchDialog.addEventListener('keydown', (event) => {
  const rows = [...document.querySelectorAll('#search-results .search-result')];
  if (!rows.length) return;
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault();
    const direction = event.key === 'ArrowDown' ? 1 : -1;
    selectedSearchResult = (selectedSearchResult + direction + rows.length) % rows.length;
    rows.forEach((row, index) => row.classList.toggle('is-selected', index === selectedSearchResult));
  } else if (event.key === 'Enter') {
    event.preventDefault();
    activateSearchResult(rows[selectedSearchResult]);
  }
});

document.addEventListener('keydown', (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault();
    openSearch();
  }
  if (event.key === 'Escape') document.querySelector('#sidebar').classList.remove('is-open');
});

renderCurrentView();
