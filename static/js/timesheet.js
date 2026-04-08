/**
 * Shared timesheet interactions for staff detail and overview screens.
 */

document.addEventListener('DOMContentLoaded', function() {
    initDateRangeForm({
        formId: 'timesheetFilterForm',
        startId: 'timesheet_start',
        endId: 'timesheet_end',
        addQuickRanges: true,
        quickRangeHandler: 'setDateRange',
    });

    initDateRangeForm({
        formId: 'timesheetOverviewFilterForm',
        startId: 'overview_start_date',
        endId: 'overview_end_date',
    });

    enhanceExportButtons();
    initTimesheetAnimations();
});

function initDateRangeForm(options) {
    const form = document.getElementById(options.formId);
    const startInput = document.getElementById(options.startId);
    const endInput = document.getElementById(options.endId);

    if (!form || !startInput || !endInput) {
        return;
    }

    const alertContainer = form.closest('.card-body') || form.parentElement;
    const handleDateChange = function() {
        validateDateRange(startInput, endInput, alertContainer);

        if (startInput.value && endInput.value) {
            form.submit();
        }
    };

    startInput.addEventListener('change', handleDateChange);
    endInput.addEventListener('change', handleDateChange);

    if (options.addQuickRanges) {
        addQuickDateRangeButtons(form, options.quickRangeHandler);
    }
}

function validateDateRange(startInput, endInput, alertContainer) {
    if (!startInput.value || !endInput.value) {
        return;
    }

    const startDate = new Date(startInput.value);
    const endDate = new Date(endInput.value);

    if (endDate < startDate) {
        endInput.value = startInput.value;
        showAlert(
            'End date cannot be before start date. Adjusted automatically.',
            'warning',
            alertContainer
        );
    }
}

function addQuickDateRangeButtons(form, quickRangeHandler) {
    if (!form || form.querySelector('.timesheet-quick-ranges')) {
        return;
    }

    const quickRangeDiv = document.createElement('div');
    quickRangeDiv.className = 'col-12 mb-2 timesheet-quick-ranges';
    quickRangeDiv.innerHTML = `
        <small class="text-muted">Quick ranges:</small>
        <div class="btn-group btn-group-sm ms-2" role="group">
            <button type="button" class="btn btn-outline-secondary" onclick="${quickRangeHandler}('today')">Today</button>
            <button type="button" class="btn btn-outline-secondary" onclick="${quickRangeHandler}('week')">This Week</button>
            <button type="button" class="btn btn-outline-secondary" onclick="${quickRangeHandler}('month')">This Month</button>
            <button type="button" class="btn btn-outline-secondary" onclick="${quickRangeHandler}('last30')">Last 30 Days</button>
        </div>
    `;

    form.insertBefore(quickRangeDiv, form.firstElementChild);
}

function setDateRange(period) {
    setDateRangeForForm('timesheet_start', 'timesheet_end', 'timesheetFilterForm', period);
}

function setOverviewDateRange(period) {
    setDateRangeForForm(
        'overview_start_date',
        'overview_end_date',
        'timesheetOverviewFilterForm',
        period
    );
}

function setDateRangeForForm(startId, endId, formId, period) {
    const startInput = document.getElementById(startId);
    const endInput = document.getElementById(endId);
    const form = document.getElementById(formId);

    if (!startInput || !endInput) {
        return;
    }

    const today = new Date();
    let startDate;
    let endDate;

    switch (period) {
        case 'today':
            startDate = today;
            endDate = today;
            break;
        case 'week': {
            const dayOfWeek = today.getDay();
            const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
            startDate = new Date(today);
            startDate.setDate(today.getDate() - daysToMonday);
            endDate = today;
            break;
        }
        case 'month':
            startDate = new Date(today.getFullYear(), today.getMonth(), 1);
            endDate = today;
            break;
        case 'last30':
            startDate = new Date(today);
            startDate.setDate(today.getDate() - 30);
            endDate = today;
            break;
        default:
            return;
    }

    startInput.value = formatDateForInput(startDate);
    endInput.value = formatDateForInput(endDate);

    if (form) {
        form.submit();
    }
}

function formatDateForInput(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function enhanceExportButtons() {
    const exportButtons = document.querySelectorAll('a[href*="timesheet/export"]');

    exportButtons.forEach(button => {
        button.addEventListener('click', function() {
            const originalText = this.innerHTML;
            const originalClass = this.className;

            this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Exporting...';
            this.className = originalClass.replace('btn-outline-', 'btn-');
            this.style.pointerEvents = 'none';

            setTimeout(() => {
                this.innerHTML = originalText;
                this.className = originalClass;
                this.style.pointerEvents = 'auto';
            }, 5000);
        });
    });
}

function showAlert(message, type = 'info', container = null) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    const targetContainer = container || document.querySelector('.card-body') || document.querySelector('.container');
    if (targetContainer) {
        targetContainer.insertBefore(alertDiv, targetContainer.firstChild);

        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 3000);
    }
}

function initTimesheetAnimations() {
    const summaryCards = document.querySelectorAll('.fw-bold.fs-4');

    summaryCards.forEach(card => {
        card.style.transition = 'transform 0.2s ease-in-out';
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.1)';
        });
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });
}

window.setDateRange = setDateRange;
window.setOverviewDateRange = setOverviewDateRange;
