/**
 * Timesheet panel functionality
 * Handles date filtering and interactive features for staff timesheet
 */

// Auto-submit the timesheet filter form when dates change
document.addEventListener('DOMContentLoaded', function() {
    const timesheetForm = document.getElementById('timesheetFilterForm');
    const startDateInput = document.getElementById('timesheet_start');
    const endDateInput = document.getElementById('timesheet_end');
    
    if (timesheetForm && startDateInput && endDateInput) {
        // Auto-submit when either date changes
        startDateInput.addEventListener('change', function() {
            if (this.value && endDateInput.value) {
                timesheetForm.submit();
            }
        });
        
        endDateInput.addEventListener('change', function() {
            if (this.value && startDateInput.value) {
                timesheetForm.submit();
            }
        });
        
        // Validate date range - end date should not be before start date
        function validateDateRange() {
            if (startDateInput.value && endDateInput.value) {
                const startDate = new Date(startDateInput.value);
                const endDate = new Date(endDateInput.value);
                
                if (endDate < startDate) {
                    endDateInput.value = startDateInput.value;
                    showAlert('End date cannot be before start date. Adjusted automatically.', 'warning');
                }
            }
        }
        
        startDateInput.addEventListener('change', validateDateRange);
        endDateInput.addEventListener('change', validateDateRange);
    }
    
    // Add quick date range buttons
    addQuickDateRangeButtons();
    
    // Enhanced export functionality with loading states
    enhanceExportButtons();
});

/**
 * Add quick date range selection buttons
 */
function addQuickDateRangeButtons() {
    const filterForm = document.getElementById('timesheetFilterForm');
    if (!filterForm) return;
    
    // Create quick range container
    const quickRangeDiv = document.createElement('div');
    quickRangeDiv.className = 'col-12 mb-2';
    quickRangeDiv.innerHTML = `
        <small class="text-muted">Quick ranges:</small>
        <div class="btn-group btn-group-sm ms-2" role="group">
            <button type="button" class="btn btn-outline-secondary" onclick="setDateRange('today')">Today</button>
            <button type="button" class="btn btn-outline-secondary" onclick="setDateRange('week')">This Week</button>
            <button type="button" class="btn btn-outline-secondary" onclick="setDateRange('month')">This Month</button>
            <button type="button" class="btn btn-outline-secondary" onclick="setDateRange('last30')">Last 30 Days</button>
        </div>
    `;
    
    // Insert before the first row or at the top of the form
    const firstRow = filterForm.querySelector('.row');
    if (firstRow) {
        firstRow.parentNode.insertBefore(quickRangeDiv, firstRow);
    } else {
        filterForm.insertBefore(quickRangeDiv, filterForm.firstElementChild);
    }
}

/**
 * Set date range based on predefined periods
 */
function setDateRange(period) {
    const startInput = document.getElementById('timesheet_start');
    const endInput = document.getElementById('timesheet_end');
    const form = document.getElementById('timesheetFilterForm');
    
    if (!startInput || !endInput) return;
    
    const today = new Date();
    let startDate, endDate;
    
    switch (period) {
        case 'today':
            startDate = endDate = today;
            break;
            
        case 'week':
            // Start of current week (Monday)
            const dayOfWeek = today.getDay();
            const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
            startDate = new Date(today);
            startDate.setDate(today.getDate() - daysToMonday);
            endDate = today;
            break;
            
        case 'month':
            // Start of current month
            startDate = new Date(today.getFullYear(), today.getMonth(), 1);
            endDate = today;
            break;
            
        case 'last30':
            // Last 30 days
            startDate = new Date(today);
            startDate.setDate(today.getDate() - 30);
            endDate = today;
            break;
            
        default:
            return;
    }
    
    // Format dates for input fields (YYYY-MM-DD)
    startInput.value = formatDateForInput(startDate);
    endInput.value = formatDateForInput(endDate);
    
    // Submit form
    if (form) {
        form.submit();
    }
}

/**
 * Format date for HTML date input (YYYY-MM-DD)
 */
function formatDateForInput(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

/**
 * Enhance export buttons with loading states and error handling
 */
function enhanceExportButtons() {
    const exportButtons = document.querySelectorAll('a[href*="timesheet/export"]');
    
    exportButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Add loading state
            const originalText = this.innerHTML;
            const originalClass = this.className;
            
            this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Exporting...';
            this.className = originalClass.replace('btn-outline-', 'btn-');
            this.style.pointerEvents = 'none';
            
            // Reset button state after a timeout (in case of errors)
            setTimeout(() => {
                this.innerHTML = originalText;
                this.className = originalClass;
                this.style.pointerEvents = 'auto';
            }, 5000);
        });
    });
}

/**
 * Show alert message with auto-dismiss
 */
function showAlert(message, type = 'info') {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Find container to insert alert
    const container = document.querySelector('.card-body') || document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-dismiss after 3 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 3000);
    }
}

/**
 * Initialize timesheet summary animations
 */
function initTimesheetAnimations() {
    const summaryCards = document.querySelectorAll('.fw-bold.fs-4');
    
    summaryCards.forEach(card => {
        // Add hover effect
        card.style.transition = 'transform 0.2s ease-in-out';
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.1)';
        });
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });
}

// Initialize animations when DOM is ready
document.addEventListener('DOMContentLoaded', initTimesheetAnimations);
