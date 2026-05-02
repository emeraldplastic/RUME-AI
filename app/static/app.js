const App = {
    user: null,
    token: "",
    jobs: [],
    currentJobId: null,
    currentJobTitle: "",
    currentFilter: "all",
    currentSort: "score",
    candidates: [],
    editingJobId: null,

    init() {
        this.bindAuth();
        this.bindNavigation();
        this.bindJobs();
        this.bindUpload();
        this.bindResults();
        this.bindModal();
        this.checkAuth();
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
        document.getElementById("filter-bar").addEventListener("click", (event) => {
            const button = event.target.closest(".filter-chip");
            if (!button) return;
            this.currentFilter = button.dataset.filter;
            document.querySelectorAll(".filter-chip").forEach((chip) => chip.classList.remove("active"));
            button.classList.add("active");
            this.loadResults();
        });
        document.getElementById("btn-export").addEventListener("click", () => this.exportCsv());
        document.getElementById("candidates-list").addEventListener("click", (event) => {
            const card = event.target.closest("[data-candidate-id]");
            if (card) this.showCandidate(Number(card.dataset.candidateId));
        });
    },

    bindModal() {
        document.getElementById("modal-close").addEventListener("click", () => this.closeModal());
        document.getElementById("modal-overlay").addEventListener("click", (event) => {
            if (event.target.id === "modal-overlay") this.closeModal();
        });
    },

    async apiFetch(url, options = {}) {
        const headers = options.headers || {};
        if (this.token) headers.Authorization = `Bearer ${this.token}`;
        if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
        const response = await fetch(url, { ...options, headers, credentials: "same-origin" });
        if (response.status === 401) {
            this.token = "";
            this.showAuth();
        }
        return response;
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
        await this.submitAuth("/api/auth/login", { username, password }, "Signed in");
    },

    async register(event) {
        event.preventDefault();
        const payload = {
            username: document.getElementById("reg-username").value.trim(),
            email: document.getElementById("reg-email").value.trim(),
            display_name: document.getElementById("reg-display").value.trim(),
            password: document.getElementById("reg-password").value,
        };
        await this.submitAuth("/api/auth/register", payload, "Account created");
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
            this.token = data.token || "";
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
        await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" });
        this.token = "";
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
    },

    async loadDashboard() {
        const response = await this.apiFetch("/api/dashboard");
        if (!response.ok) return;
        const data = await response.json();
        const stats = data.stats;
        document.getElementById("dash-total-jobs").textContent = stats.total_jobs;
        document.getElementById("dash-total-resumes").textContent = stats.total_resumes;
        document.getElementById("dash-analyzed").textContent = stats.analyzed;
        document.getElementById("dash-avg-score").textContent = stats.average_score;
        this.renderRecentJobs(data.recent_jobs || []);
        this.renderActivity(data.recent_activity || []);
    },

    renderRecentJobs(jobs) {
        const target = document.getElementById("dash-recent-jobs");
        if (!jobs.length) {
            target.innerHTML = `<div class="empty">No jobs yet.</div>`;
            return;
        }
        target.innerHTML = jobs.map((job) => `
            <div class="list-row">
                <div>
                    <button data-job-action="open" data-id="${job.id}" data-title="${this.escapeAttr(job.title)}">${this.escape(job.title)}</button>
                    <div class="meta">${job.resume_count} resumes - ${this.formatDate(job.updated_at)}</div>
                </div>
                <span class="chip ${this.statusColor(job.status)}">${this.escape(job.status)}</span>
            </div>
        `).join("");
    },

    renderActivity(items) {
        const target = document.getElementById("dash-activity");
        if (!items.length) {
            target.innerHTML = `<div class="empty">No audit activity yet.</div>`;
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
            grid.innerHTML = `<div class="empty">No jobs created yet.</div>`;
            return;
        }
        grid.innerHTML = this.jobs.map((job) => `
            <article class="job-card">
                <h3 class="job-title">${this.escape(job.title)}</h3>
                <div class="job-meta">
                    <span class="chip ${this.statusColor(job.status)}">${this.escape(job.status)}</span>
                    <span class="chip">${job.resume_count} resumes</span>
                    <span class="chip">${job.min_experience}+ yrs</span>
                    <span class="chip">${this.escape(job.min_education)}</span>
                </div>
                <div class="card-actions">
                    <button class="btn btn-primary" data-job-action="open" data-id="${job.id}" data-title="${this.escapeAttr(job.title)}" type="button">Open</button>
                    <button class="btn btn-secondary" data-job-action="edit" data-id="${job.id}" type="button">Edit</button>
                    <button class="btn btn-secondary" data-job-action="delete" data-id="${job.id}" type="button">Delete</button>
                </div>
            </article>
        `).join("");
    },

    resetJobForm() {
        this.editingJobId = null;
        document.getElementById("job-form-heading").textContent = "Create job";
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
        this.showLoading(this.editingJobId ? "Updating job..." : "Creating job...");
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
        this.showLoading("Loading job...");
        try {
            const response = await this.apiFetch(`/api/jobs/${id}`);
            const job = await response.json();
            if (!response.ok) throw new Error(job.error || "Could not load job");
            this.editingJobId = id;
            document.getElementById("job-form-heading").textContent = "Edit job";
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
        if (!window.confirm("Delete this job and its encrypted resume records?")) return;
        const response = await this.apiFetch(`/api/jobs/${id}`, { method: "DELETE" });
        if (response.ok) {
            this.toast("Job deleted", "success");
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
        select.innerHTML = `<option value="">Select a job</option>` + this.jobs.map((job) => (
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
            <div class="file-row">
                <div>
                    <strong>${this.escape(candidate.filename)}</strong>
                    <div class="meta">${this.escape(candidate.candidate_name)} - ${candidate.extracted_skills.length} skills</div>
                </div>
                <span class="chip blue">${this.escape(candidate.education_level || "parsed")}</span>
            </div>
        `).join("") : `<div class="empty">No resumes uploaded for this job.</div>`;
    },

    async uploadFiles(files) {
        if (!this.currentJobId) {
            this.toast("Select a job before uploading resumes.", "error");
            return;
        }
        const form = new FormData();
        Array.from(files).forEach((file) => form.append("resumes", file));
        this.showLoading(`Uploading ${files.length} file(s)...`);
        try {
            const response = await this.apiFetch(`/api/jobs/${this.currentJobId}/upload`, { method: "POST", body: form });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Upload failed");
            const message = data.errors?.length ? `${data.uploaded} uploaded, ${data.errors.length} skipped` : `${data.uploaded} uploaded`;
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
        this.showLoading("Analyzing resumes...");
        try {
            const response = await this.apiFetch(`/api/jobs/${this.currentJobId}/analyze`, { method: "POST" });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Analysis failed");
            this.renderSummary(data);
            this.toast("Analysis complete", "success");
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
            list.innerHTML = `<div class="empty">Open a job, upload resumes, and run analysis.</div>`;
            return;
        }
        const params = new URLSearchParams({ sort: this.currentSort, status: this.currentFilter });
        const response = await this.apiFetch(`/api/jobs/${this.currentJobId}/results?${params.toString()}`);
        if (!response.ok) return;
        const data = await response.json();
        this.currentJobTitle = data.job.title;
        this.candidates = data.candidates || [];
        document.getElementById("results-title").textContent = `Results: ${data.job.title}`;
        this.renderSummaryFromCandidates(this.candidates);
        this.renderCandidates(this.candidates);
    },

    renderSummary(data) {
        document.getElementById("result-summary").innerHTML = `
            <div class="summary-card"><span>Total</span><strong>${data.total}</strong></div>
            <div class="summary-card"><span>Qualified</span><strong>${data.qualified}</strong></div>
            <div class="summary-card"><span>Not qualified</span><strong>${data.not_qualified}</strong></div>
            <div class="summary-card"><span>Average</span><strong>${data.average_score}</strong></div>
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
            list.innerHTML = `<div class="empty">No candidates match this view.</div>`;
            return;
        }
        list.innerHTML = candidates.map((candidate, index) => {
            const analysis = candidate.analysis || {};
            const status = analysis.status || "pending";
            const score = analysis.overall_score || 0;
            return `
                <article class="candidate-card" data-candidate-id="${candidate.id}">
                    <span class="rank">${index + 1}</span>
                    <div>
                        <h3 class="candidate-name">${this.escape(candidate.candidate_name || "Unknown candidate")}</h3>
                        <div class="candidate-meta">
                            <span>${this.escape(candidate.candidate_email_masked || "No email")}</span>
                            <span>${candidate.years_experience || 0} yrs</span>
                            <span>${this.escape(candidate.education_level || "not specified")}</span>
                        </div>
                    </div>
                    <div class="score-wrap">
                        <span class="chip ${this.analysisColor(status)}">${this.escape(status.replaceAll("_", " "))}</span>
                        <span class="score status-${status}">${score}</span>
                    </div>
                </article>
            `;
        }).join("");
    },

    showCandidate(id) {
        const candidate = this.candidates.find((item) => item.id === id);
        if (!candidate || !candidate.analysis) return;
        const analysis = candidate.analysis;
        document.getElementById("modal-title").textContent = candidate.candidate_name || "Candidate";
        const matched = this.splitList(analysis.matched_skills);
        const missing = this.splitList(analysis.missing_skills);
        const strengths = this.splitList(analysis.strengths, "|");
        const weaknesses = this.splitList(analysis.weaknesses, "|");
        document.getElementById("modal-body").innerHTML = `
            <div class="score-grid">
                ${this.scoreTile("Overall", analysis.overall_score)}
                ${this.scoreTile("Skills", analysis.skill_score)}
                ${this.scoreTile("Experience", analysis.experience_score)}
                ${this.scoreTile("Education", analysis.education_score)}
                ${this.scoreTile("Relevance", analysis.similarity_score)}
            </div>
            <div class="section-title">Matched skills</div>
            <div class="skill-list">${matched.length ? matched.map((s) => `<span class="chip green">${this.escape(s)}</span>`).join("") : `<span class="chip">None</span>`}</div>
            <div class="section-title">Missing skills</div>
            <div class="skill-list">${missing.length ? missing.map((s) => `<span class="chip red">${this.escape(s)}</span>`).join("") : `<span class="chip green">No major gaps</span>`}</div>
            <div class="section-title">Strengths</div>
            <ul class="insight-list">${strengths.map((s) => `<li>${this.escape(s)}</li>`).join("")}</ul>
            <div class="section-title">Areas to review</div>
            <ul class="insight-list">${weaknesses.map((s) => `<li>${this.escape(s)}</li>`).join("")}</ul>
            <div class="section-title">Assessment</div>
            <div class="explanation">${this.escape(analysis.explanation || "")}</div>
        `;
        document.getElementById("modal-overlay").hidden = false;
    },

    closeModal() {
        document.getElementById("modal-overlay").hidden = true;
    },

    scoreTile(label, value) {
        return `<div class="score-tile"><span>${label}</span><strong>${value || 0}</strong></div>`;
    },

    exportCsv() {
        if (!this.candidates.length) {
            this.toast("No candidates to export.", "error");
            return;
        }
        const rows = [["Rank", "Candidate", "Masked Email", "Score", "Status", "Matched Skills", "Missing Skills", "Experience", "Education"]];
        this.candidates.forEach((candidate, index) => {
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
        this.toast("CSV exported", "success");
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
        if (seconds < 60) return "now";
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
        return `${Math.floor(seconds / 86400)}d`;
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
