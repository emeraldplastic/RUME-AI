const App = {
    user: null,
    jobs: [],
    currentJobId: null,
    currentJobTitle: "",
    currentFilter: "all",
    currentSort: "score",
    currentSearch: "",
    blindReview: false,
    candidates: [],
    editingJobId: null,

    init() {
        this.bindAuth();
        this.bindPasswordToggles();
        this.bindNavigation();
        this.bindJobs();
        this.bindUpload();
        this.bindResults();
        this.bindModal();
        this.bindTrust();
        this.checkAuth();
    },

    bindPasswordToggles() {
        document.querySelectorAll(".password-toggle-btn").forEach((btn) => {
            btn.addEventListener("click", () => {
                const targetId = btn.dataset.target;
                const input = document.getElementById(targetId);
                if (input) {
                    const isPassword = input.type === "password";
                    input.type = isPassword ? "text" : "password";
                    btn.innerHTML = isPassword
                        ? `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`
                        : `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
                }
            });
        });
    },

    bindAuth() {
        document.getElementById("tab-login").addEventListener("click", () => this.showAuthTab("login"));
        document.getElementById("tab-register").addEventListener("click", () => this.showAuthTab("register"));
        document.getElementById("login-form").addEventListener("submit", (event) => this.login(event));
        document.getElementById("register-form").addEventListener("submit", (event) => this.register(event));
        document.getElementById("btn-logout").addEventListener("click", () => this.logout());
        document.getElementById("btn-mobile-logout").addEventListener("click", () => this.logout());
    },

    bindNavigation() {
        document.querySelectorAll(".nav-item").forEach((item) => {
            item.addEventListener("click", () => this.navigate(item.dataset.view));
        });
        document.querySelectorAll("[data-action='new-job']").forEach((button) => {
            button.addEventListener("click", () => {
                this.resetJobForm();
                this.navigate("job-form");
            });
        });
        document.querySelector("[data-action='cancel-job']").addEventListener("click", () => this.navigate("jobs"));
        document.getElementById("btn-menu").addEventListener("click", () => {
            document.getElementById("sidebar").classList.toggle("open");
        });
    },

    bindJobs() {
        document.getElementById("job-form").addEventListener("submit", (event) => this.saveJob(event));
        document.getElementById("jobs-grid").addEventListener("click", (event) => {
            const button = event.target.closest("[data-job-action]");
            if (!button) return;
            const id = Number(button.dataset.id);
            const action = button.dataset.jobAction;
            if (action === "open") this.openJob(id, button.dataset.title || "");
            if (action === "edit") this.editJob(id);
            if (action === "delete") this.deleteJob(id);
        });
        document.getElementById("dash-recent-jobs").addEventListener("click", (event) => {
            const button = event.target.closest("[data-job-action='open']");
            if (button) this.openJob(Number(button.dataset.id), button.dataset.title || "");
        });
    },

    bindUpload() {
        const zone = document.getElementById("upload-zone");
        const input = document.getElementById("file-input");
        zone.addEventListener("dragover", (event) => {
            event.preventDefault();
            zone.classList.add("dragover");
        });
        zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
        zone.addEventListener("drop", (event) => {
            event.preventDefault();
            zone.classList.remove("dragover");
            if (event.dataTransfer.files.length) this.uploadFiles(event.dataTransfer.files);
        });
        input.addEventListener("change", () => {
            if (input.files.length) this.uploadFiles(input.files);
        });
        document.getElementById("upload-job-select").addEventListener("change", (event) => {
            this.currentJobId = Number(event.target.value) || null;
            this.currentJobTitle = event.target.selectedOptions[0]?.textContent || "";
            this.loadUploadedResumes();
        });
        document.getElementById("btn-analyze").addEventListener("click", () => this.runAnalysis());
    },

    bindResults() {
        document.getElementById("sort-select").addEventListener("change", (event) => {
            this.currentSort = event.target.value;
            this.loadResults();
        });
        document.getElementById("result-search").addEventListener("input", (event) => {
            this.currentSearch = event.target.value.trim().toLowerCase();
            const visible = this.filteredCandidates();
            this.renderSummaryFromCandidates(visible);
            this.renderCandidates(visible);
        });
        document.getElementById("filter-bar").addEventListener("click", (event) => {
            const button = event.target.closest(".filter-chip");
            if (!button) return;
            this.currentFilter = button.dataset.filter;
            document.querySelectorAll(".filter-chip").forEach((chip) => chip.classList.remove("active"));
            button.classList.add("active");
            this.loadResults();
        });
        document.getElementById("btn-export").addEventListener("click", () => this.exportCsv());
        document.getElementById("btn-audit-pack").addEventListener("click", () => this.exportAuditPack());
        document.getElementById("btn-skill-gap").addEventListener("click", () => this.showSkillGapAnalysis());
        document.getElementById("blind-review-toggle").addEventListener("change", (event) => {
            this.blindReview = event.target.checked;
            this.loadResults();
        });
        document.getElementById("candidates-list").addEventListener("click", (event) => {
            const deleteButton = event.target.closest("[data-candidate-action='delete']");
            if (deleteButton) {
                event.stopPropagation();
                this.deleteCandidate(Number(deleteButton.dataset.id));
                return;
            }
            const card = event.target.closest("[data-candidate-id]");
            if (card) this.showCandidate(Number(card.dataset.candidateId));
        });
    },

    bindModal() {
        document.getElementById("modal-close").addEventListener("click", () => this.closeModal());
        document.getElementById("modal-overlay").addEventListener("click", (event) => {
            if (event.target.id === "modal-overlay") this.closeModal();
        });
        document.getElementById("modal-body").addEventListener("submit", (event) => {
            if (event.target.id === "decision-form") this.submitDecision(event);
        });

        // Skill gap modal
        const skillGapModal = document.getElementById("modal-skill-gap");
        if (skillGapModal) {
            document.getElementById("skill-gap-close").addEventListener("click", () => {
                skillGapModal.hidden = true;
            });
            skillGapModal.addEventListener("click", (event) => {
                if (event.target.id === "modal-skill-gap") skillGapModal.hidden = true;
            });
        }
    },

    bindTrust() {
        document.getElementById("btn-refresh-trust").addEventListener("click", () => this.loadTrust());
        document.getElementById("btn-search-logs").addEventListener("click", () => this.loadLogs());
    },

    async apiFetch(url, options = {}) {
        const headers = options.headers || {};
        const method = (options.method || "GET").toUpperCase();
        const csrfToken = this.readCookie("csrf_token");
        if (csrfToken && !["GET", "HEAD", "OPTIONS"].includes(method)) {
            headers["X-CSRF-Token"] = csrfToken;
        }
        if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
        const response = await fetch(url, { ...options, headers, credentials: "same-origin" });
        if (response.status === 401) {
            this.user = null;
            this.showAuth();
        }
        return response;
    },

    readCookie(name) {
        const value = document.cookie
            .split("; ")
            .find((row) => row.startsWith(`${name}=`))
            ?.split("=")
            .slice(1)
            .join("=") || "";
        return decodeURIComponent(value);
    },

    async checkAuth() {
        try {
            const response = await this.apiFetch("/api/auth/me");
            if (!response.ok) throw new Error("not signed in");
            const data = await response.json();
            this.user = data.user;
            this.showApp();
        } catch {
            this.showAuth();
        }
    },

    showAuthTab(tab) {
        document.querySelectorAll(".auth-tab").forEach((button) => button.classList.remove("active"));
        document.querySelectorAll(".auth-form").forEach((form) => form.classList.remove("active"));
        document.getElementById(`tab-${tab}`).classList.add("active");
        document.getElementById(`${tab}-form`).classList.add("active");
    },

    showAuth() {
        document.getElementById("auth-wrapper").hidden = false;
        document.getElementById("app-shell").hidden = true;
    },

    showApp() {
        const name = this.user?.display_name || this.user?.username || "User";
        document.getElementById("auth-wrapper").hidden = true;
        document.getElementById("app-shell").hidden = false;
        document.getElementById("user-name").textContent = name;
        document.getElementById("user-avatar").textContent = name.charAt(0).toUpperCase();
        document.getElementById("greeting").textContent = `Welcome back, ${name}`;
        this.navigate("dashboard");
    },

    async login(event) {
        event.preventDefault();
        const username = document.getElementById("login-username").value.trim();
        const password = document.getElementById("login-password").value;
        await this.submitAuth("/api/auth/login", { username, password }, "Signed in successfully");
    },

    async register(event) {
        event.preventDefault();
        const payload = {
            username: document.getElementById("reg-username").value.trim(),
            email: document.getElementById("reg-email").value.trim(),
            display_name: document.getElementById("reg-display").value.trim(),
            password: document.getElementById("reg-password").value,
        };
        await this.submitAuth("/api/auth/register", payload, "Account created successfully");
    },

    async submitAuth(url, payload, message) {
        this.showLoading("Signing you in...");
        try {
            const response = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                body: JSON.stringify(payload),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Authentication failed");
            this.user = data.user;
            this.toast(message, "success");
            this.showApp();
        } catch (error) {
            this.toast(error.message, "error");
        } finally {
            this.hideLoading();
        }
    },

    async logout() {
        await this.apiFetch("/api/auth/logout", { method: "POST" });
        this.user = null;
        this.showAuth();
    },

    navigate(view) {
        document.querySelectorAll(".view").forEach((section) => section.classList.toggle("active", section.id === `view-${view}`));
        document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
        document.getElementById("sidebar").classList.remove("open");
        if (view === "dashboard") this.loadDashboard();
        if (view === "jobs") this.loadJobs();
        if (view === "upload") this.prepareUpload();
        if (view === "results") this.loadResults();
        if (view === "trust") this.loadTrust();
    },

    async loadDashboard() {
        const response = await this.apiFetch("/api/dashboard");
        if (!response.ok) return;
        const data = await response.json();
        const stats = data.stats;
        document.getElementById("dash-total-jobs").textContent = stats.total_jobs;
        document.getElementById("dash-total-resumes").textContent = stats.total_resumes;
        document.getElementById("dash-analyzed").textContent = stats.analyzed;
        document.getElementById("dash-avg-score").textContent = `${stats.average_score}%`;
        this.renderRecentJobs(data.recent_jobs || []);
        this.renderActivity(data.recent_activity || []);
    },

    renderRecentJobs(jobs) {
        const target = document.getElementById("dash-recent-jobs");
        if (!jobs.length) {
            target.innerHTML = `<div class="empty">No jobs created yet. Click "+ New Job" to get started.</div>`;
            return;
        }
        target.innerHTML = jobs.map((job) => `
            <div class="list-row">
                <div>
                    <button data-job-action="open" data-id="${job.id}" data-title="${this.escapeAttr(job.title)}">${this.escape(job.title)}</button>
                    <div class="meta">${job.resume_count} resumes • Updated ${this.formatDate(job.updated_at)}</div>
                </div>
                <span class="chip ${this.statusColor(job.status)}">${this.escape(job.status)}</span>
            </div>
        `).join("");
    },

    renderActivity(items) {
        const target = document.getElementById("dash-activity");
        if (!items.length) {
            target.innerHTML = `<div class="empty">No audit activity recorded yet.</div>`;
            return;
        }
        target.innerHTML = items.map((item) => `
            <div class="list-row">
                <div>
                    <strong>${this.escape(item.action.replaceAll("_", " "))}</strong>
                    <div class="meta">${this.escape(item.detail || "")}</div>
                </div>
                <span class="meta">${this.timeAgo(item.timestamp)}</span>
            </div>
        `).join("");
    },

    async loadJobs() {
        const response = await this.apiFetch("/api/jobs");
        if (!response.ok) return;
        this.jobs = await response.json();
        const grid = document.getElementById("jobs-grid");
        if (!this.jobs.length) {
            grid.innerHTML = `<div class="empty">No jobs created yet. Create a job to start parsing resumes.</div>`;
            return;
        }
        grid.innerHTML = this.jobs.map((job) => `
            <article class="job-card glass-panel">
                <h3 class="job-title">${this.escape(job.title)}</h3>
                <div class="job-meta">
                    <span class="chip ${this.statusColor(job.status)}">${this.escape(job.status)}</span>
                    <span class="chip">${job.resume_count} resumes</span>
                    <span class="chip">${job.min_experience}+ yrs exp</span>
                    <span class="chip">${this.escape(job.min_education)}</span>
                </div>
                <div class="card-actions">
                    <button class="btn btn-primary" data-job-action="open" data-id="${job.id}" data-title="${this.escapeAttr(job.title)}" type="button">Open Workspace</button>
                    <button class="btn btn-secondary" data-job-action="edit" data-id="${job.id}" type="button">Edit</button>
                    <button class="btn btn-secondary" data-job-action="delete" data-id="${job.id}" type="button">Delete</button>
                </div>
            </article>
        `).join("");
    },

    resetJobForm() {
        this.editingJobId = null;
        document.getElementById("job-form-heading").textContent = "Create job position";
        document.getElementById("job-form").reset();
        document.getElementById("min-experience").value = "2";
        document.getElementById("min-education").value = "bachelor";
    },

    async saveJob(event) {
        event.preventDefault();
        const payload = {
            title: document.getElementById("job-title").value.trim(),
            description: document.getElementById("job-description").value.trim(),
            required_skills: document.getElementById("required-skills").value.trim(),
            min_experience: Number(document.getElementById("min-experience").value || 0),
            min_education: document.getElementById("min-education").value,
        };
        if (!payload.title || !payload.description) {
            this.toast("Job title and description are required.", "error");
            return;
        }
        this.showLoading(this.editingJobId ? "Updating job requirements..." : "Creating job workspace...");
        try {
            const url = this.editingJobId ? `/api/jobs/${this.editingJobId}` : "/api/jobs";
            const method = this.editingJobId ? "PUT" : "POST";
            const response = await this.apiFetch(url, { method, body: JSON.stringify(payload) });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Could not save job");
            this.toast(this.editingJobId ? "Job updated" : "Job created", "success");
            this.editingJobId = null;
            this.navigate("jobs");
        } catch (error) {
            this.toast(error.message, "error");
        } finally {
            this.hideLoading();
        }
    },

    async editJob(id) {
        this.showLoading("Loading job details...");
        try {
            const response = await this.apiFetch(`/api/jobs/${id}`);
            const job = await response.json();
            if (!response.ok) throw new Error(job.error || "Could not load job");
            this.editingJobId = id;
            document.getElementById("job-form-heading").textContent = "Edit job position";
            document.getElementById("job-title").value = job.title;
            document.getElementById("job-description").value = job.description;
            document.getElementById("required-skills").value = job.required_skills;
            document.getElementById("min-experience").value = job.min_experience;
            document.getElementById("min-education").value = job.min_education;
            this.navigate("job-form");
        } catch (error) {
            this.toast(error.message, "error");
        } finally {
            this.hideLoading();
        }
    },

    async deleteJob(id) {
        if (!window.confirm("Delete this job and all associated candidate records?")) return;
        const response = await this.apiFetch(`/api/jobs/${id}`, { method: "DELETE" });
        if (response.ok) {
            this.toast("Job position deleted", "success");
            this.loadJobs();
            this.loadDashboard();
        } else {
            const data = await response.json();
            this.toast(data.error || "Could not delete job", "error");
        }
    },

    openJob(id, title) {
        this.currentJobId = id;
        this.currentJobTitle = title;
        this.navigate("upload");
    },

    async prepareUpload() {
        await this.loadJobOptions();
        if (this.currentJobId) document.getElementById("upload-job-select").value = String(this.currentJobId);
        await this.loadUploadedResumes();
    },

    async loadJobOptions() {
        const response = await this.apiFetch("/api/jobs");
        if (!response.ok) return;
        this.jobs = await response.json();
        const select = document.getElementById("upload-job-select");
        select.innerHTML = `<option value="">Select a job position</option>` + this.jobs.map((job) => (
            `<option value="${job.id}">${this.escape(job.title)}</option>`
        )).join("");
    },

    async loadUploadedResumes() {
        const list = document.getElementById("uploaded-files");
        const analyzeButton = document.getElementById("btn-analyze");
        list.innerHTML = "";
        analyzeButton.disabled = true;
        if (!this.currentJobId) return;
        const response = await this.apiFetch(`/api/jobs/${this.currentJobId}`);
        if (!response.ok) return;
        const job = await response.json();
        this.currentJobTitle = job.title;
        const candidates = job.candidates || [];
        analyzeButton.disabled = candidates.length === 0;
        list.innerHTML = candidates.length ? candidates.map((candidate) => `
            <div class="file-item">
                <div class="file-item-name">
                    📄 <strong>${this.escape(candidate.filename)}</strong>
                    <span class="meta">(${this.escape(candidate.candidate_name)} • ${candidate.extracted_skills.length} skills identified)</span>
                </div>
                <span class="chip blue">${this.escape(candidate.education_level || "Parsed")}</span>
            </div>
        `).join("") : `<div class="empty">No resumes uploaded yet for this role. Drop PDF or DOCX files above.</div>`;
    },

    async uploadFiles(files) {
        if (!this.currentJobId) {
            this.toast("Please select a target job position first.", "error");
            return;
        }
        const form = new FormData();
        Array.from(files).forEach((file) => form.append("resumes", file));
        this.showLoading(`Encrypting & uploading ${files.length} file(s)...`);
        try {
            const response = await this.apiFetch(`/api/jobs/${this.currentJobId}/upload`, { method: "POST", body: form });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Upload failed");
            const message = data.errors?.length ? `${data.uploaded} uploaded, ${data.errors.length} skipped` : `${data.uploaded} resume(s) uploaded successfully`;
            this.toast(message, data.errors?.length ? "error" : "success");
            if (data.errors?.length) data.errors.slice(0, 3).forEach((item) => this.toast(item, "error"));
            document.getElementById("file-input").value = "";
            await this.loadUploadedResumes();
            await this.loadDashboard();
        } catch (error) {
            this.toast(error.message, "error");
        } finally {
            this.hideLoading();
        }
    },

    async runAnalysis() {
        if (!this.currentJobId) return;
        this.showLoading("Running AI semantic matching & fit scoring...");
        try {
            const response = await this.apiFetch(`/api/jobs/${this.currentJobId}/analyze`, { method: "POST" });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Analysis failed");
            this.renderSummary(data);
            this.toast("AI Candidate Analysis completed!", "success");
            this.navigate("results");
        } catch (error) {
            this.toast(error.message, "error");
        } finally {
            this.hideLoading();
        }
    },

    async loadResults() {
        const summary = document.getElementById("result-summary");
        const list = document.getElementById("candidates-list");
        if (!this.currentJobId) {
            summary.innerHTML = "";
            list.innerHTML = `<div class="empty">Select a job position to view ranked candidates.</div>`;
            return;
        }
        document.getElementById("blind-review-toggle").checked = this.blindReview;
        const params = new URLSearchParams({
            sort: this.currentSort,
            status: this.currentFilter,
            blind: this.blindReview ? "1" : "0",
        });
        const response = await this.apiFetch(`/api/jobs/${this.currentJobId}/results?${params.toString()}`);
        if (!response.ok) return;
        const data = await response.json();
        this.currentJobTitle = data.job.title;
        this.candidates = data.candidates || [];
        document.getElementById("results-title").textContent = `Ranking: ${data.job.title}`;
        const visible = this.filteredCandidates();
        this.renderSummaryFromCandidates(visible);
        this.renderCandidates(visible);
    },

    renderSummary(data) {
        document.getElementById("result-summary").innerHTML = `
            <div class="summary-card glass-panel"><span>Total Applicants</span><strong>${data.total}</strong></div>
            <div class="summary-card glass-panel"><span>Highly Qualified</span><strong>${data.qualified}</strong></div>
            <div class="summary-card glass-panel"><span>Skill Gaps / Unqualified</span><strong>${data.not_qualified}</strong></div>
            <div class="summary-card glass-panel"><span>Avg Fit Score</span><strong>${data.average_score}%</strong></div>
        `;
    },

    renderSummaryFromCandidates(candidates) {
        const total = candidates.length;
        const qualified = candidates.filter((c) => c.analysis && ["highly_qualified", "qualified"].includes(c.analysis.status)).length;
        const scores = candidates.map((c) => c.analysis?.overall_score || 0);
        const average = scores.length ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1) : "0";
        this.renderSummary({ total, qualified, not_qualified: total - qualified, average_score: average });
    },

    renderCandidates(candidates) {
        const list = document.getElementById("candidates-list");
        if (!candidates.length) {
            list.innerHTML = `<div class="empty">No candidates found for this filter/search query.</div>`;
            return;
        }
        list.innerHTML = candidates.map((candidate, index) => {
            const analysis = candidate.analysis || {};
            const status = analysis.status || "pending";
            const score = analysis.overall_score || 0;
            return `
                <article class="candidate-card glass-panel hover-lift" data-candidate-id="${candidate.id}">
                    <span class="rank">#${index + 1}</span>
                    <div>
                        <h3 class="candidate-name">
                            ${this.escape(candidate.candidate_name || "Candidate #" + candidate.id)}
                            ${candidate.latest_decision ? `<span class="chip status">${this.escape(candidate.latest_decision.decision.replaceAll("_", " "))}</span>` : ""}
                        </h3>
                        <div class="candidate-meta">
                            <span>📧 ${this.escape(candidate.candidate_email_masked || "Hidden PII")}</span> • 
                            <span>⏳ ${candidate.years_experience || 0} yrs exp</span> • 
                            <span>🎓 ${this.escape(candidate.education_level || "Degree not specified")}</span>
                        </div>
                    </div>
                    <div class="score-wrap">
                        <span class="chip ${this.analysisColor(status)}">${this.escape(status.replaceAll("_", " "))}</span>
                        <span class="score status-${status}">${score}%</span>
                        <button class="icon-btn danger" data-candidate-action="delete" data-id="${candidate.id}" type="button" title="Remove candidate" aria-label="Remove candidate">
                            <svg viewBox="0 0 24 24"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 15H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>
                        </button>
                    </div>
                </article>
            `;
        }).join("");
    },

    filteredCandidates() {
        if (!this.currentSearch) return this.candidates;
        return this.candidates.filter((candidate) => {
            const analysis = candidate.analysis || {};
            const haystack = [
                candidate.candidate_name,
                candidate.candidate_email_masked,
                candidate.education_level,
                candidate.extracted_skills?.join(" "),
                analysis.status?.replaceAll("_", " "),
                analysis.matched_skills,
                analysis.missing_skills,
            ].join(" ").toLowerCase();
            return haystack.includes(this.currentSearch);
        });
    },

    async deleteCandidate(id) {
        if (!this.currentJobId || !window.confirm("Permanently delete this encrypted candidate record?")) return;
        const response = await this.apiFetch(`/api/jobs/${this.currentJobId}/candidates/${id}`, { method: "DELETE" });
        if (response.ok) {
            this.toast("Candidate removed", "success");
            await this.loadResults();
            await this.loadDashboard();
            return;
        }
        const data = await response.json();
        this.toast(data.error || "Could not remove candidate", "error");
    },

    showCandidate(id) {
        const candidate = this.candidates.find((item) => item.id === id);
        if (!candidate || !candidate.analysis) return;
        const analysis = candidate.analysis;
        document.getElementById("modal-title").textContent = candidate.candidate_name || "Candidate Details";
        const matched = this.splitList(analysis.matched_skills);
        const missing = this.splitList(analysis.missing_skills);
        const strengths = this.splitList(analysis.strengths, "|");
        const weaknesses = this.splitList(analysis.weaknesses, "|");
        const latestDecision = candidate.latest_decision;
        document.getElementById("modal-body").innerHTML = `
            <div class="score-grid">
                ${this.scoreTile("Overall Fit", `${analysis.overall_score}%`)}
                ${this.scoreTile("Skill Score", `${analysis.skill_score}%`)}
                ${this.scoreTile("Experience", `${analysis.experience_score}%`)}
                ${this.scoreTile("Education", `${analysis.education_score}%`)}
                ${this.scoreTile("Relevance", `${analysis.similarity_score}%`)}
            </div>
            <div class="section-title">Matched Skills</div>
            <div class="skill-list">${matched.length ? matched.map((s) => `<span class="chip matched">✓ ${this.escape(s)}</span>`).join("") : `<span class="chip">None</span>`}</div>
            <div class="section-title">Missing / Gap Skills</div>
            <div class="skill-list">${missing.length ? missing.map((s) => `<span class="chip missing">! ${this.escape(s)}</span>`).join("") : `<span class="chip green">✓ No major skill gaps</span>`}</div>
            <div class="section-title">Key Candidate Strengths</div>
            <ul class="insight-list">${strengths.map((s) => `<li>${this.escape(s)}</li>`).join("")}</ul>
            <div class="section-title">Areas to Review</div>
            <ul class="insight-list">${weaknesses.map((s) => `<li>${this.escape(s)}</li>`).join("")}</ul>
            <div class="section-title">Resume Evidence Snippets</div>
            ${this.renderEvidence(analysis.evidence || {})}
            <div class="section-title">AI Rationale</div>
            <div class="explanation">${this.escape(analysis.explanation || "")}</div>
            <form class="decision-form" id="decision-form" data-resume-id="${candidate.id}">
                <div class="section-title">Hiring Decision Journal</div>
                <label>Decision
                    <select id="decision-select" class="glass-input">
                        <option value="manual_review">Manual review required</option>
                        <option value="advance">Advance to interview</option>
                        <option value="hold">Hold on file</option>
                        <option value="reject">Reject</option>
                        <option value="needs_info">Needs additional info</option>
                    </select>
                </label>
                <label>Reviewer Notes
                    <textarea id="decision-note" class="glass-input" rows="3" placeholder="Add evidence-backed feedback for the hiring team...">${this.escape(latestDecision?.note || "")}</textarea>
                </label>
                ${latestDecision ? `<div class="meta" style="margin-top:8px;">Latest decision: <strong>${this.escape(latestDecision.decision.replaceAll("_", " "))}</strong> • Updated ${this.formatDate(latestDecision.updated_at)}</div>` : ""}
                <div class="form-actions">
                    <button class="btn btn-primary glowing-btn" type="submit">Save Decision</button>
                </div>
            </form>
        `;
        if (latestDecision) document.getElementById("decision-select").value = latestDecision.decision;
        document.getElementById("modal-overlay").hidden = false;
    },

    renderEvidence(evidence) {
        const matched = evidence.matched_skills || {};
        const skillRows = Object.entries(matched).flatMap(([skill, rows]) => (
            (rows || []).map((row) => `
                <div class="evidence-item">
                    <strong>Skill: ${this.escape(skill)}</strong>
                    <div>"${this.escape(row.snippet || "")}"</div>
                    <div class="meta">Line ${row.line || "?"} • Matched term: ${this.escape(row.term || skill)}</div>
                </div>
            `)
        ));
        const experienceRows = (evidence.experience?.evidence || []).map((row) => `
            <div class="evidence-item">
                <strong>Work Experience</strong>
                <div>"${this.escape(row.snippet || "")}"</div>
                <div class="meta">Line ${row.line || "?"}</div>
            </div>
        `);
        const educationRows = (evidence.education?.evidence || []).map((row) => `
            <div class="evidence-item">
                <strong>Education Fit</strong>
                <div>"${this.escape(row.snippet || "")}"</div>
                <div class="meta">Line ${row.line || "?"}</div>
            </div>
        `);
        const rows = [...skillRows, ...experienceRows, ...educationRows];
        return rows.length ? `<div class="evidence-list">${rows.join("")}</div>` : `<div class="empty">No specific line evidence required.</div>`;
    },

    async submitDecision(event) {
        event.preventDefault();
        const resumeId = Number(event.target.dataset.resumeId);
        if (!this.currentJobId || !resumeId) return;
        const payload = {
            decision: document.getElementById("decision-select").value,
            note: document.getElementById("decision-note").value.trim(),
        };
        try {
            const response = await this.apiFetch(`/api/jobs/${this.currentJobId}/candidates/${resumeId}/decision`, {
                method: "POST",
                body: JSON.stringify(payload),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Could not save decision");
            this.toast("Hiring decision saved", "success");
            await this.loadResults();
            this.closeModal();
        } catch (error) {
            this.toast(error.message, "error");
        }
    },

    async showSkillGapAnalysis() {
        if (!this.currentJobId) {
            this.toast("Open a job to analyze skill gaps.", "error");
            return;
        }
        const modal = document.getElementById("modal-skill-gap");
        const body = document.getElementById("skill-gap-body");
        modal.hidden = false;
        body.innerHTML = `<div class="loading-overlay" style="position:relative; min-height:200px;"><div class="loader"></div><p>Calculating skill coverage...</p></div>`;

        try {
            const response = await this.apiFetch(`/api/jobs/${this.currentJobId}/skill-gap-analysis`);
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Could not fetch skill gap analysis");

            const coveragePct = data.coverage_percentage || 0;
            const requiredSkills = data.required_skills || [];
            const missingSummary = data.missing_skills_summary || {};
            const learningRecs = data.learning_recommendations || {};

            body.innerHTML = `
                <div class="score-tile glass-panel" style="margin-bottom:20px;">
                    <span>Pipeline Skill Coverage</span>
                    <strong style="color:var(--accent-cyan); font-size:2.2rem;">${coveragePct}%</strong>
                    <p class="meta" style="margin-top:6px;">${data.covered_skills_count || 0} of ${requiredSkills.length} required skills covered by applicant pool</p>
                </div>

                <div class="section-title">Top Skill Gaps in Candidate Pool</div>
                <div class="skill-list">
                    ${Object.entries(missingSummary).length ? Object.entries(missingSummary).map(([skill, count]) => `
                        <div class="chip missing" style="padding:6px 14px;">
                            <strong>${this.escape(skill)}</strong>: missing in ${count} resume(s)
                        </div>
                    `).join("") : `<div class="chip green">No major skill gaps identified in your candidate pipeline!</div>`}
                </div>

                <div class="section-title">Recommended Upskilling Courses</div>
                <div class="list">
                    ${Object.entries(learningRecs).map(([skill, recs]) => `
                        <div class="list-row" style="flex-direction:column; align-items:flex-start;">
                            <strong>Skill: ${this.escape(skill)}</strong>
                            <ul style="margin-left:20px; font-size:0.9rem; color:var(--text-muted);">
                                ${recs.map(r => `<li>${this.escape(r.title || r.name || r)}</li>`).join("")}
                            </ul>
                        </div>
                    `).join("")}
                </div>
            `;
        } catch (error) {
            body.innerHTML = `<div class="toast error">${this.escape(error.message)}</div>`;
        }
    },

    closeModal() {
        document.getElementById("modal-overlay").hidden = true;
    },

    scoreTile(label, value) {
        return `<div class="score-tile"><span>${label}</span><strong>${value || 0}</strong></div>`;
    },

    exportCsv() {
        const candidates = this.filteredCandidates();
        if (!candidates.length) {
            this.toast("No candidates to export.", "error");
            return;
        }
        const rows = [["Rank", "Candidate", "Masked Email", "Score", "Status", "Matched Skills", "Missing Skills", "Experience", "Education"]];
        candidates.forEach((candidate, index) => {
            const analysis = candidate.analysis || {};
            rows.push([
                index + 1,
                candidate.candidate_name || "",
                candidate.candidate_email_masked || "",
                analysis.overall_score || 0,
                (analysis.status || "").replaceAll("_", " "),
                analysis.matched_skills || "",
                analysis.missing_skills || "",
                candidate.years_experience || 0,
                candidate.education_level || "",
            ]);
        });
        const csv = rows.map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(",")).join("\n");
        const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `rume-ai-${(this.currentJobTitle || "results").toLowerCase().replace(/[^a-z0-9]+/g, "-")}.csv`;
        link.click();
        URL.revokeObjectURL(url);
        this.toast("CSV exported successfully", "success");
    },

    async exportAuditPack() {
        if (!this.currentJobId) {
            this.toast("Open a job before exporting an audit pack.", "error");
            return;
        }
        try {
            const response = await this.apiFetch(`/api/jobs/${this.currentJobId}/audit-pack`);
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Could not export audit pack");
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = `rume-ai-audit-${(this.currentJobTitle || "job").toLowerCase().replace(/[^a-z0-9]+/g, "-")}.json`;
            link.click();
            URL.revokeObjectURL(url);
            this.toast("Audit pack exported", "success");
        } catch (error) {
            this.toast(error.message, "error");
        }
    },

    async loadTrust() {
        await Promise.all([this.loadCalibrations(), this.loadLogs()]);
    },

    async loadCalibrations() {
        const target = document.getElementById("trust-calibrations");
        if (!this.currentJobId) {
            target.innerHTML = `<div class="empty">Open a job position to see calibration history.</div>`;
            return;
        }
        const response = await this.apiFetch(`/api/jobs/${this.currentJobId}/calibrations`);
        if (!response.ok) return;
        const data = await response.json();
        const calibrations = data.calibrations || [];
        target.innerHTML = calibrations.length ? calibrations.map((item) => `
            <div class="list-row">
                <div>
                    <strong>Version ${item.version}</strong>
                    <div class="meta">Skills: ${this.escape((item.criteria.required_skills_normalized || []).join(", "))}</div>
                    <code style="font-size:0.75rem; color:var(--accent-cyan);">${this.escape(item.criteria_hash.slice(0, 16))}</code>
                </div>
                <span class="meta">${this.formatDate(item.created_at)}</span>
            </div>
        `).join("") : `<div class="empty">No analysis calibration version created yet.</div>`;
    },

    async loadLogs() {
        const target = document.getElementById("trust-logs");
        const params = new URLSearchParams({ limit: "40" });
        const requestId = document.getElementById("log-request-id").value.trim();
        const level = document.getElementById("log-level").value;
        if (requestId) params.set("request_id", requestId);
        if (level) params.set("level", level);
        const response = await this.apiFetch(`/api/logs?${params.toString()}`);
        if (!response.ok) return;
        const data = await response.json();
        const logs = data.logs || [];
        target.innerHTML = logs.length ? logs.map((item) => `
            <div class="list-row log-row">
                <div>
                    <strong>${this.escape(item.event)}</strong>
                    <div class="meta">${this.escape(item.method || "")} ${this.escape(item.path || "")} • HTTP ${item.status_code || "200"} • ${item.duration_ms || 0}ms</div>
                    <code style="font-size:0.75rem; color:var(--text-muted);">${this.escape(item.request_id)}</code>
                </div>
                <span class="log-badge ${item.level === "error" ? "error" : "info"}">${this.escape(item.level)}</span>
            </div>
        `).join("") : `<div class="empty">No logs matched your query.</div>`;
    },

    showLoading(text) {
        document.getElementById("loading-text").textContent = text;
        document.getElementById("loading-overlay").hidden = false;
    },

    hideLoading() {
        document.getElementById("loading-overlay").hidden = true;
    },

    toast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.textContent = message;
        document.getElementById("toast-container").appendChild(toast);
        setTimeout(() => toast.remove(), 4200);
    },

    splitList(value, delimiter = ",") {
        return (value || "").split(delimiter).map((item) => item.trim()).filter(Boolean);
    },

    formatDate(value) {
        if (!value) return "";
        return new Date(value).toLocaleDateString();
    },

    timeAgo(value) {
        if (!value) return "";
        const seconds = Math.max(0, (Date.now() - new Date(value).getTime()) / 1000);
        if (seconds < 60) return "just now";
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        return `${Math.floor(seconds / 86400)}d ago`;
    },

    statusColor(status) {
        if (status === "active") return "green";
        if (status === "closed") return "red";
        return "amber";
    },

    analysisColor(status) {
        if (status === "highly_qualified") return "green";
        if (status === "qualified") return "blue";
        if (status === "partially_qualified") return "amber";
        if (status === "not_qualified") return "red";
        return "";
    },

    escape(value) {
        const div = document.createElement("div");
        div.textContent = value == null ? "" : String(value);
        return div.innerHTML;
    },

    escapeAttr(value) {
        return this.escape(value).replaceAll("'", "&#39;");
    },
};

document.addEventListener("DOMContentLoaded", () => App.init());
