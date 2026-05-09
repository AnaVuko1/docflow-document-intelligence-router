/**
 * DocFlow Pipelines JavaScript
 * Handles pipeline management and execution
 */

// Pipelines module
const Pipelines = (function() {
    // Private variables
    let yamlEditor = null;
    let pipelineRunner = null;
    
    /**
     * Initialize pipelines page
     */
    function init() {
        console.log('Initializing DocFlow pipelines...');
        
        // Initialize YAML editor if available
        initYamlEditor();
        
        // Load pipelines
        loadPipelines();
        
        // Set up event listeners
        setupEventListeners();
    }
    
    /**
     * Initialize YAML editor
     */
    function initYamlEditor() {
        const editorElement = document.getElementById('yamlEditor');
        if (!editorElement) return;
        
        // Check if Ace editor is available
        if (typeof ace !== 'undefined') {
            yamlEditor = ace.edit('yamlEditor');
            yamlEditor.setTheme('ace/theme/chrome');
            yamlEditor.session.setMode('ace/mode/yaml');
            yamlEditor.setOptions({
                fontSize: '14px',
                showPrintMargin: false,
                highlightActiveLine: true,
                enableBasicAutocompletion: true,
                enableLiveAutocompletion: false
            });
            
            // Sync with textarea
            const textarea = document.getElementById('pipelineYaml');
            if (textarea) {
                yamlEditor.session.on('change', function() {
                    textarea.value = yamlEditor.getValue();
                });
                
                // Load template into editor
                loadBasicTemplate();
            }
        } else {
            console.warn('Ace editor not available');
        }
    }
    
    /**
     * Set up event listeners
     */
    function setupEventListeners() {
        // Template buttons
        document.querySelectorAll('.template-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const template = this.dataset.template;
                loadTemplate(template);
            });
        });
        
        // Create pipeline form
        const createForm = document.getElementById('createPipelineForm');
        if (createForm) {
            createForm.addEventListener('submit', function(e) {
                e.preventDefault();
                createPipeline();
            });
        }
        
        // Search input
        const searchInput = document.getElementById('searchPipelines');
        if (searchInput) {
            searchInput.addEventListener('input', function() {
                filterPipelines(this.value);
            });
        }
        
        // Status filter
        const statusFilter = document.getElementById('filterStatus');
        if (statusFilter) {
            statusFilter.addEventListener('change', function() {
                filterPipelinesByStatus(this.value);
            });
        }
    }
    
    /**
     * Load pipelines
     */
    async function loadPipelines() {
        try {
            showLoading('pipelinesBody', 'Loading pipelines...');
            
            const response = await fetch('/api/v1/pipelines');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            updatePipelinesTable(data.items);
            
        } catch (error) {
            console.error('Error loading pipelines:', error);
            showError('pipelinesBody', 'Failed to load pipelines');
        }
    }
    
    /**
     * Update pipelines table
     * @param {Array} pipelines - List of pipelines
     */
    function updatePipelinesTable(pipelines) {
        const tbody = document.getElementById('pipelinesBody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        if (pipelines.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center text-muted py-4">
                        <i class="fas fa-project-diagram fa-2x mb-3 d-block"></i>
                        No pipelines found. Create your first pipeline!
                    </td>
                </tr>
            `;
            return;
        }
        
        pipelines.forEach(pipeline => {
            const row = document.createElement('tr');
            row.dataset.pipelineId = pipeline.id;
            
            // Count steps
            const stepCount = pipeline.definition?.steps?.length || 0;
            
            // Format date
            const updated = new Date(pipeline.updated_at || pipeline.created_at);
            const dateStr = updated.toLocaleDateString() + ' ' + updated.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            
            // Status badge
            const statusBadge = pipeline.is_active 
                ? '<span class="badge bg-success">Active</span>' 
                : '<span class="badge bg-secondary">Inactive</span>';
            
            // Action buttons
            const actions = `
                <div class="btn-group btn-group-sm" role="group">
                    <button type="button" class="btn btn-outline-primary" 
                            onclick="Pipelines.viewPipeline(${pipeline.id})">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button type="button" class="btn btn-outline-success" 
                            onclick="Pipelines.runPipeline(${pipeline.id})">
                        <i class="fas fa-play"></i>
                    </button>
                    <button type="button" class="btn btn-outline-warning" 
                            onclick="Pipelines.editPipeline(${pipeline.id})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button type="button" class="btn btn-outline-danger" 
                            onclick="Pipelines.deletePipeline(${pipeline.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
            
            row.innerHTML = `
                <td>${pipeline.id}</td>
                <td>
                    <strong>${pipeline.name}</strong>
                    <br>
                    <small class="text-muted">${pipeline.description || 'No description'}</small>
                </td>
                <td>${pipeline.version}</td>
                <td>${stepCount} step${stepCount !== 1 ? 's' : ''}</td>
                <td>${statusBadge}</td>
                <td>${dateStr}</td>
                <td>${actions}</td>
            `;
            
            tbody.appendChild(row);
        });
    }
    
    /**
     * Filter pipelines by search term
     * @param {string} searchTerm - Search term
     */
    function filterPipelines(searchTerm) {
        const rows = document.querySelectorAll('#pipelinesBody tr');
        const term = searchTerm.toLowerCase().trim();
        
        rows.forEach(row => {
            if (term === '') {
                row.style.display = '';
                return;
            }
            
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(term) ? '' : 'none';
        });
    }
    
    /**
     * Filter pipelines by status
     * @param {string} status - Status filter
     */
    function filterPipelinesByStatus(status) {
        const rows = document.querySelectorAll('#pipelinesBody tr');
        
        rows.forEach(row => {
            if (status === 'all') {
                row.style.display = '';
                return;
            }
            
            const statusCell = row.querySelector('td:nth-child(5)');
            if (!statusCell) return;
            
            const isActive = statusCell.innerHTML.includes('Active');
            const shouldShow = (status === 'active' && isActive) || (status === 'inactive' && !isActive);
            
            row.style.display = shouldShow ? '' : 'none';
        });
    }
    
    /**
     * Load YAML template
     * @param {string} templateName - Template name
     */
    function loadTemplate(templateName) {
        if (!yamlEditor) return;
        
        const templates = {
            empty: `name: "New Pipeline"
description: "Describe your pipeline here"
steps: []`,
            
            basic: `name: "Basic Document Processor"
description: "Classify and extract basic fields from documents"
steps:
  - type: classify
    config:
      target_types: [invoice, receipt, contract, generic]
  
  - type: extract
    config:
      strategy: regex
      fields:
        - name: date
          pattern: "Date\\\\s*[:]?\\\\s*(\\\\d{1,2}[/-]\\\\d{1,2}[/-]\\\\d{2,4})"
        
        - name: total
          pattern: "Total\\\\s*[:$]?\\\\s*([\\\\d,]+\\\\.?\\\\d{0,2})"
  
  - type: route
    config:
      destinations:
        - type: csv
          filename: "output.csv"`,
            
            advanced: `name: "Advanced Invoice Processor"
description: "Complete invoice processing with validation and routing"
steps:
  - type: classify
    name: "Document Classification"
    config:
      target_types: [invoice, receipt]
  
  - type: extract
    name: "Field Extraction"
    config:
      strategy: regex
      fields:
        - name: invoice_number
          pattern: "Invoice\\\\s*#?\\\\s*([A-Z0-9-]+)"
          required: true
        
        - name: date
          pattern: "Date\\\\s*[:]?\\\\s*(\\\\d{1,2}[/-]\\\\d{1,2}[/-]\\\\d{2,4})"
        
        - name: total_amount
          pattern: "Total\\\\s*[:$]?\\\\s*([\\\\d,]+\\\\.\\\\d{2})"
          required: true
  
  - type: validate
    name: "Data Validation"
    config:
      rules:
        - field: total_amount
          rule: "value > 0"
          message: "Total amount must be positive"
        
        - field: invoice_number
          rule: "len(value) >= 3"
          message: "Invoice number must be at least 3 characters"
  
  - type: transform
    name: "Data Transformation"
    config:
      mappings:
        invoice_number: "invoice_id"
        total_amount: "amount"
      
      formats:
        - field: amount
          format: float
        
        - field: date
          format: date
          params:
            output_format: "%Y-%m-%d"
  
  - type: route
    name: "Output Routing"
    config:
      destinations:
        - type: csv
          filename: "invoices.csv"
        
        - type: sqlite
          table: "processed_invoices"`
        };
        
        const template = templates[templateName] || templates.basic;
        yamlEditor.setValue(template);
        yamlEditor.clearSelection();
        
        showToast(`Loaded ${templateName} template`, 'success');
    }
    
    /**
     * Load basic template (legacy compatibility)
     */
    function loadBasicTemplate() {
        loadTemplate('basic');
    }
    
    /**
     * Create a new pipeline
     */
    async function createPipeline() {
        try {
            const name = document.getElementById('pipelineName').value.trim();
            const description = document.getElementById('pipelineDescription').value.trim();
            const yamlContent = document.getElementById('pipelineYaml').value.trim();
            const isActive = document.getElementById('pipelineActive').checked;
            
            if (!name) {
                showToast('Pipeline name is required', 'danger');
                return;
            }
            
            if (!yamlContent) {
                showToast('Pipeline definition is required', 'danger');
                return;
            }
            
            // Parse YAML
            let definition;
            try {
                // Try to parse as YAML
                if (typeof jsyaml !== 'undefined') {
                    definition = jsyaml.load(yamlContent);
                } else {
                    // Fallback to JSON parsing
                    definition = JSON.parse(yamlContent);
                }
            } catch (e) {
                showToast(`Invalid YAML/JSON: ${e.message}`, 'danger');
                return;
            }
            
            // Validate definition
            if (!definition.name || !definition.steps) {
                showToast('Pipeline definition must include name and steps fields', 'danger');
                return;
            }
            
            const pipelineData = {
                name: name,
                description: description || null,
                definition: definition,
                is_active: isActive
            };
            
            const response = await fetch('/api/v1/pipelines', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(pipelineData)
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to create pipeline');
            }
            
            const pipeline = await response.json();
            
            // Close modal and reset form
            const modal = bootstrap.Modal.getInstance(document.getElementById('createPipelineModal'));
            if (modal) modal.hide();
            
            document.getElementById('createPipelineForm').reset();
            if (yamlEditor) yamlEditor.setValue('');
            
            // Show success and reload
            showToast(`Pipeline "${pipeline.name}" created successfully`, 'success');
            setTimeout(() => loadPipelines(), 1000);
            
        } catch (error) {
            console.error('Error creating pipeline:', error);
            showToast(`Failed to create pipeline: ${error.message}`, 'danger');
        }
    }
    
    /**
     * View pipeline details
     * @param {number} pipelineId - Pipeline ID
     */
    async function viewPipeline(pipelineId) {
        try {
            const response = await fetch(`/api/v1/pipelines/${pipelineId}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const pipeline = await response.json();
            
            // Create modal content
            const modalContent = `
                <div class="modal-header">
                    <h5 class="modal-title">${pipeline.name}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-4">
                        <h6>Description</h6>
                        <p>${pipeline.description || 'No description provided.'}</p>
                    </div>
                    
                    <div class="mb-4">
                        <h6>Pipeline Steps (${pipeline.definition?.steps?.length || 0})</h6>
                        <div class="list-group">
                            ${(pipeline.definition?.steps || []).map((step, index) => `
                                <div class="list-group-item">
                                    <div class="d-flex w-100 justify-content-between">
                                        <h6 class="mb-1">Step ${index + 1}: ${step.type}</h6>
                                        <small>${step.name || 'Unnamed'}</small>
                                    </div>
                                    <pre class="mb-1" style="font-size: 0.8em;">${JSON.stringify(step.config, null, 2)}</pre>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <h6>Metadata</h6>
                        <dl class="row">
                            <dt class="col-sm-3">ID</dt>
                            <dd class="col-sm-9">${pipeline.id}</dd>
                            
                            <dt class="col-sm-3">Version</dt>
                            <dd class="col-sm-9">${pipeline.version}</dd>
                            
                            <dt class="col-sm-3">Status</dt>
                            <dd class="col-sm-9">
                                ${pipeline.is_active 
                                    ? '<span class="badge bg-success">Active</span>' 
                                    : '<span class="badge bg-secondary">Inactive</span>'}
                            </dd>
                        </dl>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    <button type="button" class="btn btn-primary" onclick="Pipelines.editPipeline(${pipeline.id})">
                        Edit Pipeline
                    </button>
                </div>
            `;
            
            // Create and show modal
            showModal('Pipeline Details', modalContent, 'lg');
            
        } catch (error) {
            console.error('Error viewing pipeline:', error);
            showToast('Failed to load pipeline details', 'danger');
        }
    }
    
    /**
     * Run a pipeline
     * @param {number} pipelineId - Pipeline ID
     */
    async function runPipeline(pipelineId) {
        try {
            const response = await fetch(`/api/v1/pipelines/${pipelineId}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const pipeline = await response.json();
            
            // Load documents for selection
            const documents = await loadDocuments();
            
            // Create modal content
            const modalContent = `
                <div class="modal-header">
                    <h5 class="modal-title">Run Pipeline: ${pipeline.name}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="runPipelineForm">
                        <div class="mb-3">
                            <label class="form-label">Input Source</label>
                            <div class="form-check mb-2">
                                <input class="form-check-input" type="radio" name="inputSource" 
                                       id="inputDocument" value="document" checked>
                                <label class="form-check-label" for="inputDocument">
                                    Use Existing Document
                                </label>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="radio" name="inputSource" 
                                       id="inputText" value="text">
                                <label class="form-check-label" for="inputText">
                                    Enter Text Content
                                </label>
                            </div>
                        </div>
                        
                        <div class="mb-3" id="documentSelection">
                            <label for="documentId" class="form-label">Select Document</label>
                            <select class="form-select" id="documentId">
                                <option value="">Select a document...</option>
                                ${documents.map(doc => `
                                    <option value="${doc.id}">
                                        ${doc.original_filename} (${doc.document_type || 'unknown'})
                                    </option>
                                `).join('')}
                            </select>
                        </div>
                        
                        <div class="mb-3 d-none" id="textContentSection">
                            <label for="contentText" class="form-label">Text Content</label>
                            <textarea class="form-control" id="contentText" rows="6" 
                                      placeholder="Paste or type document content here..."></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="Pipelines.executePipelineRun(${pipelineId})">
                        Run Pipeline
                    </button>
                </div>
            `;
            
            // Create and show modal
            const modal = showModal('Run Pipeline', modalContent);
            
            // Handle input source change
            modal.addEventListener('shown.bs.modal', function() {
                document.querySelectorAll('input[name="inputSource"]').forEach(radio => {
                    radio.addEventListener('change', function() {
                        if (this.value === 'document') {
                            document.getElementById('documentSelection').classList.remove('d-none');
                            document.getElementById('textContentSection').classList.add('d-none');
                        } else {
                            document.getElementById('documentSelection').classList.add('d-none');
                            document.getElementById('textContentSection').classList.remove('d-none');
                        }
                    });
                });
            });
            
        } catch (error) {
            console.error('Error preparing to run pipeline:', error);
            showToast('Failed to prepare pipeline run', 'danger');
        }
    }
    
    /**
     * Execute pipeline run
     * @param {number} pipelineId - Pipeline ID
     */
    async function executePipelineRun(pipelineId) {
        try {
            const inputSource = document.querySelector('input[name="inputSource"]:checked').value;
            
            let requestData = {};
            
            if (inputSource === 'document') {
                const documentId = document.getElementById('documentId').value;
                if (!documentId) {
                    showToast('Please select a document', 'danger');
                    return;
                }
                requestData.document_id = parseInt(documentId);
            } else {
                const content = document.getElementById('contentText').value.trim();
                if (!content) {
                    showToast('Please enter text content', 'danger');
                    return;
                }
                requestData.content = content;
            }
            
            const response = await fetch(`/api/v1/pipelines/${pipelineId}/run`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to run pipeline');
            }
            
            const job = await response.json();
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.querySelector('.modal.show'));
            if (modal) modal.hide();
            
            // Show success message
            showToast(`Pipeline job started! Job ID: ${job.id}`, 'success');
            
            // Redirect to job details after a delay
            setTimeout(() => {
                window.location.href = `/jobs/${job.id}`;
            }, 1500);
            
        } catch (error) {
            console.error('Error running pipeline:', error);
            showToast(`Failed to run pipeline: ${error.message}`, 'danger');
        }
    }
    
    /**
     * Edit pipeline
     * @param {number} pipelineId - Pipeline ID
     */
    async function editPipeline(pipelineId) {
        // Implementation would be similar to viewPipeline but with edit form
        showToast('Edit pipeline feature coming soon', 'info');
    }
    
    /**
     * Delete pipeline
     * @param {number} pipelineId - Pipeline ID
     */
    async function deletePipeline(pipelineId) {
        if (!confirm('Are you sure you want to delete this pipeline? This action cannot be undone.')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/v1/pipelines/${pipelineId}?soft_delete=true`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to delete pipeline');
            }
            
            const result = await response.json();
            
            showToast(result.message || 'Pipeline deleted successfully', 'success');
            setTimeout(() => loadPipelines(), 1000);
            
        } catch (error) {
            console.error('Error deleting pipeline:', error);
            showToast(`Failed to delete pipeline: ${error.message}`, 'danger');
        }
    }
    
    /**
     * Load documents for pipeline run
     * @returns {Promise<Array>} List of documents
     */
    async function loadDocuments() {
        try {
            const response = await fetch('/api/v1/documents?limit=50');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            return data.items;
            
        } catch (error) {
            console.error('Error loading documents:', error);
            return [];
        }
    }
    
    /**
     * Show loading state
     * @param {string} elementId - Element ID
     * @param {string} message - Loading message
     */
    function showLoading(elementId, message = 'Loading...') {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-4">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="mt-2 text-muted">${message}</p>
                    </td>
                </tr>
            `;
        }
    }
    
    /**
     * Show error state
     * @param {string} elementId - Element ID
     * @param {string} message - Error message
     */
    function showError(elementId, message = 'Error loading data') {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-4">
                        <i class="fas fa-exclamation-triangle fa-2x text-danger mb-3"></i>
                        <p class="text-danger">${message}</p>
                        <button class="btn btn-sm btn-outline-primary" onclick="Pipelines.loadPipelines()">
                            <i class="fas fa-redo me-1"></i>Retry
                        </button>
                    </td>
                </tr>
            `;
        }
    }
    
    /**
     * Show modal dialog
     * @param {string} title - Modal title
     * @param {string} content - Modal content
     * @param {string} size - Modal size (sm, lg, xl)
     * @returns {HTMLElement} Modal element
     */
    function showModal(title, content, size = '') {
        // Remove existing modal
        const existingModal = document.getElementById('dynamicModal');
        if (existingModal) existingModal.remove();
        
        // Create modal
        const modal = document.createElement('div');
        modal.id = 'dynamicModal';
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-${size}">
                <div class="modal-content">
                    ${content}
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Show modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        // Clean up on hide
        modal.addEventListener('hidden.bs.modal', function() {
            modal.remove();
        });
        
        return modal;
    }
    
    /**
     * Show toast notification
     * @param {string} message - Message to display
     * @param {string} type - Toast type (success, danger, etc.)
     */
    function showToast(message, type = 'info') {
        // Implementation similar to Dashboard.showToast
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-${type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                        data-bs-dismiss="toast"></button>
            </div>
        `;
        
        const container = document.getElementById('toast-container') || createToastContainer();
        container.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
    }
    
    /**
     * Create toast container
     * @returns {HTMLElement} Toast container
     */
    function createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '1055';
        document.body.appendChild(container);
        return container;
    }
    
    // Public API
    return {
        init: init,
        loadPipelines: loadPipelines,
        loadBasicTemplate: loadBasicTemplate,
        createPipeline: createPipeline,
        viewPipeline: viewPipeline,
        runPipeline: runPipeline,
        executePipelineRun: executePipelineRun,
        editPipeline: editPipeline,
        deletePipeline: deletePipeline,
        showToast: showToast
    };
})();

// Initialize pipelines when page loads
document.addEventListener('DOMContentLoaded', function() {
    Pipelines.init();
});

// Make Pipelines available globally
window.Pipelines = Pipelines;