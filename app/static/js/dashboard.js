/**
 * DocFlow Dashboard JavaScript
 * Handles dashboard functionality and data visualization
 */

// Dashboard module
const Dashboard = (function() {
    // Private variables
    let jobStatusChart = null;
    let pipelineChart = null;
    let autoRefreshInterval = null;
    
    // Configuration
    const config = {
        refreshInterval: 30000, // 30 seconds
        maxHistoryDays: 7,
        chartColors: {
            primary: '#4361ee',
            success: '#4cc9f0',
            info: '#7209b7',
            warning: '#f72585',
            danger: '#b5179e',
            secondary: '#6c757d',
            light: '#f8f9fa',
            dark: '#212529'
        }
    };
    
    /**
     * Initialize dashboard
     */
    function init() {
        console.log('Initializing DocFlow dashboard...');
        
        // Load initial data
        loadDashboardStats();
        loadRecentJobs();
        loadPipelineStats();
        
        // Set up event listeners
        setupEventListeners();
        
        // Start auto-refresh
        startAutoRefresh();
    }
    
    /**
     * Set up event listeners
     */
    function setupEventListeners() {
        // Time range selector
        const timeRangeSelect = document.getElementById('timeRangeSelect');
        if (timeRangeSelect) {
            timeRangeSelect.addEventListener('change', function() {
                loadDashboardStats(this.value);
            });
        }
        
        // Manual refresh button
        const refreshBtn = document.getElementById('refreshDashboard');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', function() {
                loadDashboardStats();
                loadRecentJobs();
                loadPipelineStats();
                showToast('Dashboard refreshed', 'success');
            });
        }
        
        // Quick action buttons
        document.querySelectorAll('.quick-action-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const action = this.dataset.action;
                handleQuickAction(action);
            });
        });
    }
    
    /**
     * Start auto-refresh interval
     */
    function startAutoRefresh() {
        if (autoRefreshInterval) {
            clearInterval(autoRefreshInterval);
        }
        
        autoRefreshInterval = setInterval(() => {
            loadDashboardStats();
            loadRecentJobs();
        }, config.refreshInterval);
    }
    
    /**
     * Load dashboard statistics
     * @param {string} timeRange - Time range filter
     */
    async function loadDashboardStats(timeRange = '7d') {
        try {
            const response = await fetch(`/api/v1/dashboard/stats?time_range=${timeRange}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const stats = await response.json();
            updateStatsDisplay(stats);
            updateJobStatusChart(stats);
            
        } catch (error) {
            console.error('Error loading dashboard stats:', error);
            showToast('Failed to load dashboard statistics', 'danger');
        }
    }
    
    /**
     * Update statistics display
     * @param {Object} stats - Statistics data
     */
    function updateStatsDisplay(stats) {
        // Update metric cards
        updateMetric('active-pipelines', stats.active_pipelines);
        updateMetric('processed-documents', stats.total_documents);
        updateMetric('total-jobs', stats.total_jobs);
        updateMetric('success-rate', `${(stats.success_rate * 100).toFixed(1)}%`);
        
        // Update jobs by status
        updateJobsByStatus(stats.jobs_by_status);
        
        // Update processing time
        const avgTime = stats.average_processing_time_ms 
            ? `${Math.round(stats.average_processing_time_ms / 1000)}s` 
            : 'N/A';
        updateMetric('avg-processing-time', avgTime);
    }
    
    /**
     * Update a metric display
     * @param {string} elementId - Element ID
     * @param {*} value - Value to display
     */
    function updateMetric(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            // Add animation if value changed
            const oldValue = element.textContent;
            if (oldValue !== String(value)) {
                element.classList.add('metric-updated');
                setTimeout(() => {
                    element.classList.remove('metric-updated');
                }, 1000);
            }
            element.textContent = value;
        }
    }
    
    /**
     * Update jobs by status display
     * @param {Object} jobsByStatus - Jobs count by status
     */
    function updateJobsByStatus(jobsByStatus) {
        const container = document.getElementById('jobsByStatus');
        if (!container) return;
        
        container.innerHTML = '';
        
        const statusOrder = ['completed', 'running', 'pending', 'failed'];
        const statusLabels = {
            completed: 'Completed',
            running: 'Running',
            pending: 'Pending',
            failed: 'Failed'
        };
        
        statusOrder.forEach(status => {
            const count = jobsByStatus[status] || 0;
            const badgeClass = getStatusBadgeClass(status);
            
            const badge = document.createElement('span');
            badge.className = `badge ${badgeClass} me-2 mb-2`;
            badge.innerHTML = `${statusLabels[status]}: <strong>${count}</strong>`;
            
            container.appendChild(badge);
        });
    }
    
    /**
     * Update job status chart
     * @param {Object} stats - Statistics data
     */
    function updateJobStatusChart(stats) {
        const ctx = document.getElementById('jobStatusChart');
        if (!ctx) return;
        
        const data = {
            labels: Object.keys(stats.jobs_by_status),
            datasets: [{
                data: Object.values(stats.jobs_by_status),
                backgroundColor: Object.keys(stats.jobs_by_status).map(status => 
                    getStatusColor(status)
                ),
                borderWidth: 1
            }]
        };
        
        if (jobStatusChart) {
            jobStatusChart.data = data;
            jobStatusChart.update();
        } else {
            jobStatusChart = new Chart(ctx, {
                type: 'doughnut',
                data: data,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 20,
                                usePointStyle: true
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return `${context.label}: ${context.raw} jobs`;
                                }
                            }
                        }
                    },
                    cutout: '70%'
                }
            });
        }
    }
    
    /**
     * Load recent jobs
     */
    async function loadRecentJobs() {
        try {
            const response = await fetch('/api/v1/jobs?limit=10&include_relations=true');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            updateRecentJobsTable(data.items);
            
        } catch (error) {
            console.error('Error loading recent jobs:', error);
            showToast('Failed to load recent jobs', 'danger');
        }
    }
    
    /**
     * Update recent jobs table
     * @param {Array} jobs - List of jobs
     */
    function updateRecentJobsTable(jobs) {
        const tbody = document.getElementById('recentJobsBody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        jobs.forEach(job => {
            const row = document.createElement('tr');
            
            // Status badge
            const badgeClass = getStatusBadgeClass(job.status);
            const statusBadge = `<span class="badge ${badgeClass}">${job.status}</span>`;
            
            // Pipeline name
            const pipelineName = job.pipeline?.name || `Pipeline ${job.pipeline_id}`;
            
            // Document name
            const documentName = job.document?.original_filename || `Document ${job.document_id}`;
            
            // Timing
            const created = job.created_at ? formatDate(job.created_at) : '-';
            let duration = '-';
            if (job.started_at && job.completed_at) {
                duration = calculateDuration(job.started_at, job.completed_at);
            }
            
            // Progress bar for running jobs
            let progressBar = '-';
            if (job.status === 'running' || job.status === 'completed') {
                const progress = job.progress || 0;
                progressBar = `
                    <div class="progress" style="height: 20px;">
                        <div class="progress-bar ${badgeClass.replace('bg-', 'bg-')}" 
                             style="width: ${progress}%">
                            ${progress}%
                        </div>
                    </div>
                `;
            }
            
            row.innerHTML = `
                <td>${job.id}</td>
                <td>${pipelineName}</td>
                <td>${documentName}</td>
                <td>${statusBadge}</td>
                <td>${progressBar}</td>
                <td>${created}</td>
                <td>${duration}</td>
                <td>
                    <a href="/jobs/${job.id}" class="btn btn-sm btn-outline-primary">
                        <i class="fas fa-eye"></i>
                    </a>
                </td>
            `;
            
            tbody.appendChild(row);
        });
    }
    
    /**
     * Load pipeline statistics
     */
    async function loadPipelineStats() {
        try {
            const response = await fetch('/api/v1/dashboard/pipelines');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const pipelines = await response.json();
            updatePipelineChart(pipelines);
            
        } catch (error) {
            console.error('Error loading pipeline stats:', error);
        }
    }
    
    /**
     * Update pipeline chart
     * @param {Array} pipelines - List of pipeline statistics
     */
    function updatePipelineChart(pipelines) {
        const ctx = document.getElementById('pipelineChart');
        if (!ctx) return;
        
        // Limit to top 5 pipelines
        const topPipelines = pipelines.slice(0, 5);
        
        const data = {
            labels: topPipelines.map(p => p.pipeline_name),
            datasets: [{
                label: 'Total Jobs',
                data: topPipelines.map(p => p.total_jobs),
                backgroundColor: config.chartColors.primary,
                borderColor: config.chartColors.primary,
                borderWidth: 1
            }]
        };
        
        if (pipelineChart) {
            pipelineChart.data = data;
            pipelineChart.update();
        } else {
            pipelineChart = new Chart(ctx, {
                type: 'bar',
                data: data,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return `Jobs: ${context.raw}`;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                precision: 0
                            }
                        }
                    }
                }
            });
        }
    }
    
    /**
     * Handle quick action
     * @param {string} action - Action identifier
     */
    function handleQuickAction(action) {
        switch(action) {
            case 'upload':
                window.location.href = '/documents/upload';
                break;
            case 'create-pipeline':
                window.location.href = '/pipelines/new';
                break;
            case 'quick-job':
                $('#quickJobModal').modal('show');
                break;
            case 'view-jobs':
                window.location.href = '/jobs';
                break;
            default:
                console.warn('Unknown quick action:', action);
        }
    }
    
    /**
     * Get CSS class for status badge
     * @param {string} status - Job status
     * @returns {string} CSS class
     */
    function getStatusBadgeClass(status) {
        switch(status.toLowerCase()) {
            case 'completed': return 'bg-success';
            case 'running': return 'bg-primary';
            case 'pending': return 'bg-warning';
            case 'failed': return 'bg-danger';
            default: return 'bg-secondary';
        }
    }
    
    /**
     * Get color for status
     * @param {string} status - Job status
     * @returns {string} Color code
     */
    function getStatusColor(status) {
        switch(status.toLowerCase()) {
            case 'completed': return config.chartColors.success;
            case 'running': return config.chartColors.primary;
            case 'pending': return config.chartColors.warning;
            case 'failed': return config.chartColors.danger;
            default: return config.chartColors.secondary;
        }
    }
    
    /**
     * Format date for display
     * @param {string} dateString - ISO date string
     * @returns {string} Formatted date
     */
    function formatDate(dateString) {
        if (!dateString) return '-';
        
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h ago`;
        
        const diffDays = Math.floor(diffHours / 24);
        if (diffDays < 7) return `${diffDays}d ago`;
        
        return date.toLocaleDateString();
    }
    
    /**
     * Calculate duration between two dates
     * @param {string} startString - Start date string
     * @param {string} endString - End date string
     * @returns {string} Formatted duration
     */
    function calculateDuration(startString, endString) {
        if (!startString || !endString) return '-';
        
        const start = new Date(startString);
        const end = new Date(endString);
        const diffMs = end - start;
        
        const seconds = Math.floor(diffMs / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        
        if (hours > 0) {
            return `${hours}h ${minutes % 60}m`;
        } else if (minutes > 0) {
            return `${minutes}m ${seconds % 60}s`;
        } else {
            return `${seconds}s`;
        }
    }
    
    /**
     * Show toast notification
     * @param {string} message - Message to display
     * @param {string} type - Toast type (success, danger, etc.)
     */
    function showToast(message, type = 'info') {
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'position-fixed bottom-0 end-0 p-3';
            toastContainer.style.zIndex = '1055';
            document.body.appendChild(toastContainer);
        }
        
        // Create toast
        const toastId = 'toast-' + Date.now();
        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                        data-bs-dismiss="toast"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        // Show toast
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove toast after it's hidden
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
    }
    
    // Public API
    return {
        init: init,
        loadDashboardStats: loadDashboardStats,
        loadRecentJobs: loadRecentJobs,
        showToast: showToast
    };
})();

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', function() {
    Dashboard.init();
});

// Make Dashboard available globally for debug
window.Dashboard = Dashboard;