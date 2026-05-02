const App = {
    token: localStorage.getItem('token'),
    init() {
        this.bindEvents();
        if (this.token) this.showApp(); else this.showAuth();
    },
    bindEvents() {
        document.getElementById('login-form').onsubmit = (e) => this.login(e);
        document.querySelectorAll('.nav-item').forEach(i => i.onclick = () => this.navigate(i.dataset.view));
        document.getElementById('btn-logout').onclick = () => this.logout();
    },
    async login(e) {
        e.preventDefault();
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        const res = await fetch('/api/auth/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username, password}) });
        if (res.ok) {
            const data = await res.json();
            this.token = data.token;
            localStorage.setItem('token', this.token);
            this.showApp();
        }
    },
    logout() {
        localStorage.removeItem('token');
        location.reload();
    },
    showApp() {
        document.getElementById('auth-wrapper').style.display = 'none';
        document.getElementById('app-shell').style.display = 'flex';
        this.loadStats();
    },
    showAuth() {
        document.getElementById('auth-wrapper').style.display = 'flex';
        document.getElementById('app-shell').style.display = 'none';
    },
    navigate(view) {
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        document.getElementById(`view-${view}`).classList.add('active');
        document.querySelectorAll('.nav-item').forEach(i => i.classList.toggle('active', i.dataset.view === view));
    },
    async loadStats() {
        const res = await fetch('/api/dashboard', { headers: {'Authorization': `Bearer ${this.token}`} });
        if (res.ok) {
            const data = await res.json();
            document.getElementById('dash-total-jobs').textContent = data.stats.total_jobs;
            document.getElementById('dash-total-resumes').textContent = data.stats.total_resumes;
            document.getElementById('dash-qualified').textContent = data.stats.qualified;
        }
    }
};
document.addEventListener('DOMContentLoaded', () => App.init());
