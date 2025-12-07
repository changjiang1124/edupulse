/**
 * Early Bird Price Adjustment Confirmation Dialog
 * Provides interface for staff to confirm price adjustments when early bird deadline has passed
 *
 * Guard against double-loading and missing bootstrap to avoid breaking the page.
 */

// Prevent double registration if the script is loaded twice
if (!window.__EARLY_BIRD_PRICE_ADJUSTMENT_LOADED__) {
    window.__EARLY_BIRD_PRICE_ADJUSTMENT_LOADED__ = true;

    class EarlyBirdPriceAdjustment {
        constructor() {
            this.modalElement = null;
            this.enrollmentId = null;
            this.adjustmentData = null;
            this.onConfirmCallback = null;
            this.createModal();
        }

    /**
     * Get CSRF token from form input or cookie
     */
    getCsrfToken() {
        const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (input && input.value) {
            return input.value;
        }
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : null;
    }

    /**
     * Create the modal HTML structure
     */
    createModal() {
        if (typeof bootstrap === 'undefined') {
            console.warn('[EarlyBird] bootstrap not available, modal will not be created');
            return;
        }

        const modalHtml = `
            <div class="modal fade" id="earlyBirdPriceModal" tabindex="-1" aria-labelledby="earlyBirdPriceModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header bg-warning">
                            <h5 class="modal-title" id="earlyBirdPriceModalLabel">
                                <i class="fas fa-exclamation-triangle me-2"></i>
                                Early Bird Price Adjustment Required
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="alert alert-info mb-3">
                                <strong>Price Adjustment Notice:</strong>
                                <p id="adjustmentReason" class="mb-0 mt-2"></p>
                            </div>

                            <div class="row">
                                <!-- Current Enrollment Information -->
                                <div class="col-md-6">
                                    <div class="card border-secondary mb-3">
                                        <div class="card-header bg-secondary text-white">
                                            <h6 class="mb-0">Current Enrollment Details</h6>
                                        </div>
                                        <div class="card-body">
                                            <table class="table table-sm table-borderless mb-0">
                                                <tr>
                                                    <td><strong>Enrollment Date:</strong></td>
                                                    <td id="enrollmentDate"></td>
                                                </tr>
                                                <tr>
                                                    <td><strong>Current Price:</strong></td>
                                                    <td id="currentPrice" class="fw-bold"></td>
                                                </tr>
                                                <tr>
                                                    <td><strong>Current Status:</strong></td>
                                                    <td id="currentStatus"></td>
                                                </tr>
                                                <tr>
                                                    <td><strong>Early Bird Deadline:</strong></td>
                                                    <td id="earlyBirdDeadline"></td>
                                                </tr>
                                            </table>
                                        </div>
                                    </div>
                                </div>

                                <!-- Course Pricing Information -->
                                <div class="col-md-6">
                                    <div class="card border-info mb-3">
                                        <div class="card-header bg-info text-white">
                                            <h6 class="mb-0">Course Pricing Options</h6>
                                        </div>
                                        <div class="card-body">
                                            <table class="table table-sm table-borderless mb-0">
                                                <tr>
                                                    <td><strong>Regular Price:</strong></td>
                                                    <td id="regularPrice" class="fw-bold"></td>
                                                </tr>
                                                <tr>
                                                    <td><strong>Early Bird Price:</strong></td>
                                                    <td id="earlyBirdPrice" class="fw-bold text-success"></td>
                                                </tr>
                                                <tr>
                                                    <td><strong>Potential Savings:</strong></td>
                                                    <td id="potentialSavings" class="fw-bold text-success"></td>
                                                </tr>
                                                <tr>
                                                    <td><strong>Action Date:</strong></td>
                                                    <td id="actionDate"></td>
                                                </tr>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Price Adjustment Options -->
                            <div class="card border-primary">
                                <div class="card-header bg-primary text-white">
                                    <h6 class="mb-0">Please Choose Price Adjustment Action</h6>
                                </div>
                                <div class="card-body">
                                    <div class="row">
                                        <div class="col-md-6">
                                            <div class="card h-100 border-success">
                                                <div class="card-body text-center">
                                                    <div class="form-check mb-3">
                                                        <input class="form-check-input" type="radio" name="priceAdjustment" id="keepEarlyBird" value="keep_early_bird">
                                                        <label class="form-check-label fw-bold text-success" for="keepEarlyBird">
                                                            Honor Early Bird Price
                                                        </label>
                                                    </div>
                                                    <div class="price-display mb-2">
                                                        <span class="h4" id="keepEarlyBirdPrice"></span>
                                                    </div>
                                                    <p class="text-muted small mb-0">
                                                        Maintain the early bird pricing that was available when the student enrolled.
                                                    </p>
                                                </div>
                                            </div>
                                        </div>
                                        <div class="col-md-6">
                                            <div class="card h-100 border-warning">
                                                <div class="card-body text-center">
                                                    <div class="form-check mb-3">
                                                        <input class="form-check-input" type="radio" name="priceAdjustment" id="applyRegular" value="apply_regular" checked>
                                                        <label class="form-check-label fw-bold text-warning" for="applyRegular">
                                                            Apply Regular Price
                                                        </label>
                                                    </div>
                                                    <div class="price-display mb-2">
                                                        <span class="h4" id="applyRegularPrice"></span>
                                                    </div>
                                                    <p class="text-muted small mb-0">
                                                        Apply the current regular pricing since the early bird deadline has passed.
                                                    </p>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Summary Section -->
                            <div class="mt-3">
                                <div class="alert alert-light border">
                                    <strong>Price Difference:</strong>
                                    <span id="priceDifference" class="fw-bold"></span>
                                    <span id="priceDifferenceDescription" class="text-muted ms-2"></span>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                <i class="fas fa-times me-1"></i>Cancel
                            </button>
                            <button type="button" class="btn btn-primary" id="confirmPriceAdjustment">
                                <i class="fas fa-check me-1"></i>Confirm Adjustment & Continue
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Add modal to body if it doesn't exist
        if (!document.getElementById('earlyBirdPriceModal')) {
            document.body.insertAdjacentHTML('beforeend', modalHtml);
        }

        this.modalElement = new bootstrap.Modal(document.getElementById('earlyBirdPriceModal'));
        this.bindEvents();
    }

    /**
     * Bind event handlers
     */
    bindEvents() {
        const modal = document.getElementById('earlyBirdPriceModal');
        const confirmBtn = modal.querySelector('#confirmPriceAdjustment');
        const priceRadios = modal.querySelectorAll('input[name="priceAdjustment"]');

        // Update price difference when radio selection changes
        priceRadios.forEach(radio => {
            radio.addEventListener('change', () => {
                this.updatePriceDifferenceDisplay();
            });
        });

        // Handle confirmation
        confirmBtn.addEventListener('click', () => {
            this.handleConfirmation();
        });
    }

    /**
     * Show the price adjustment modal
     * @param {number} enrollmentId - Enrollment ID
     * @param {Object} adjustmentData - Price adjustment data from backend
     * @param {Function} onConfirmCallback - Callback function when confirmed
     */
    show(enrollmentId, adjustmentData, onConfirmCallback = null) {
        if (typeof bootstrap === 'undefined') {
            console.warn('[EarlyBird] bootstrap missing, skipping modal');
            if (onConfirmCallback) {
                onConfirmCallback({ adjustment_made: false, skipped: 'bootstrap_missing' });
            }
            return;
        }

        this.enrollmentId = enrollmentId;
        this.adjustmentData = adjustmentData;
        this.onConfirmCallback = onConfirmCallback;

        this.populateModal(adjustmentData);
        this.modalElement.show();
    }

    /**
     * Populate modal with adjustment data
     * @param {Object} data - Adjustment data
     */
    populateModal(data) {
        const modal = document.getElementById('earlyBirdPriceModal');

        // Basic information
        modal.querySelector('#adjustmentReason').textContent = data.reason || '';
        modal.querySelector('#enrollmentDate').textContent = this.formatDate(data.enrollment_date);
        modal.querySelector('#earlyBirdDeadline').textContent = this.formatDate(data.early_bird_deadline);
        modal.querySelector('#actionDate').textContent = this.formatDate(data.action_date);
        modal.querySelector('#currentPrice').textContent = this.formatCurrency(data.current_enrollment_price);
        modal.querySelector('#currentStatus').textContent = data.current_is_early_bird ? 'Early Bird' : 'Regular';

        // Course pricing
        modal.querySelector('#regularPrice').textContent = this.formatCurrency(data.course_regular_price);
        modal.querySelector('#earlyBirdPrice').textContent = this.formatCurrency(data.course_early_bird_price);
        modal.querySelector('#potentialSavings').textContent = this.formatCurrency(data.course_early_bird_savings);

        // Option prices
        modal.querySelector('#keepEarlyBirdPrice').textContent = this.formatCurrency(data.option_keep_early_bird.price);
        modal.querySelector('#applyRegularPrice').textContent = this.formatCurrency(data.option_apply_regular.price);

        // Update price difference display
        this.updatePriceDifferenceDisplay();
    }

    /**
     * Update price difference display based on selected option
     */
    updatePriceDifferenceDisplay() {
        const modal = document.getElementById('earlyBirdPriceModal');
        const selectedOption = modal.querySelector('input[name="priceAdjustment"]:checked').value;
        const priceDiffElement = modal.querySelector('#priceDifference');
        const priceDiffDescElement = modal.querySelector('#priceDifferenceDescription');

        if (!this.adjustmentData) return;

        const currentPrice = parseFloat(this.adjustmentData.current_enrollment_price);
        let newPrice;
        let description;

        if (selectedOption === 'keep_early_bird') {
            newPrice = parseFloat(this.adjustmentData.option_keep_early_bird.price);
            description = 'keeping early bird pricing';
        } else {
            newPrice = parseFloat(this.adjustmentData.option_apply_regular.price);
            description = 'applying regular pricing';
        }

        const difference = newPrice - currentPrice;
        const absDifference = Math.abs(difference);

        if (difference > 0) {
            priceDiffElement.textContent = `+${this.formatCurrency(absDifference)}`;
            priceDiffElement.className = 'fw-bold text-danger';
            priceDiffDescElement.textContent = `(price increase by ${description})`;
        } else if (difference < 0) {
            priceDiffElement.textContent = `-${this.formatCurrency(absDifference)}`;
            priceDiffElement.className = 'fw-bold text-success';
            priceDiffDescElement.textContent = `(price decrease by ${description})`;
        } else {
            priceDiffElement.textContent = 'No change';
            priceDiffElement.className = 'fw-bold text-muted';
            priceDiffDescElement.textContent = `(${description})`;
        }
    }

    /**
     * Handle confirmation button click
     */
    async handleConfirmation() {
        const modal = document.getElementById('earlyBirdPriceModal');
        const selectedOption = modal.querySelector('input[name="priceAdjustment"]:checked').value;
        const confirmBtn = modal.querySelector('#confirmPriceAdjustment');

        // Disable button and show loading
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Processing...';

        try {
            // Apply price adjustment via AJAX
            const result = await this.applyPriceAdjustment(this.enrollmentId, selectedOption);

            if (result.success) {
                // Hide modal
                this.modalElement.hide();

                // Show success message
                this.showNotification('success', `Price adjusted successfully: ${result.message}`);

                // Call callback if provided
                if (this.onConfirmCallback) {
                    this.onConfirmCallback(result);
                }
            } else {
                throw new Error(result.message || 'Failed to apply price adjustment');
            }
        } catch (error) {
            console.error('Price adjustment error:', error);
            this.showNotification('error', `Failed to apply price adjustment: ${error.message}`);
        } finally {
            // Re-enable button
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = '<i class="fas fa-check me-1"></i>Confirm Adjustment & Continue';
        }
    }

    /**
     * Apply price adjustment via AJAX
     * @param {number} enrollmentId - Enrollment ID
     * @param {string} adjustmentType - 'keep_early_bird' or 'apply_regular'
     * @returns {Promise<Object>} - Adjustment result
     */
    async applyPriceAdjustment(enrollmentId, adjustmentType) {
        const csrfToken = this.getCsrfToken();

        if (!csrfToken) {
            throw new Error('Missing CSRF token');
        }

        const response = await fetch(`/enrollment/api/price-adjustment/${enrollmentId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                adjustment_type: adjustmentType
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Network error');
        }

        return await response.json();
    }

    /**
     * Show notification message
     * @param {string} type - 'success' or 'error'
     * @param {string} message - Message text
     */
    showNotification(type, message) {
        // Create or update notification area
        let notificationArea = document.getElementById('notification-area');
        if (!notificationArea) {
            notificationArea = document.createElement('div');
            notificationArea.id = 'notification-area';
            notificationArea.className = 'position-fixed top-0 end-0 p-3';
            notificationArea.style.zIndex = '1060';
            document.body.appendChild(notificationArea);
        }

        const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
        const iconClass = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';

        const alertHtml = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                <i class="fas ${iconClass} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;

        notificationArea.insertAdjacentHTML('beforeend', alertHtml);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            const alerts = notificationArea.querySelectorAll('.alert');
            if (alerts.length > 0) {
                alerts[0].remove();
            }
        }, 5000);
    }

    /**
     * Format currency amount
     * @param {number|string} amount - Amount to format
     * @returns {string} - Formatted currency
     */
    formatCurrency(amount) {
        const num = parseFloat(amount) || 0;
        return `$${num.toFixed(2)}`;
    }

    /**
     * Format date for display
     * @param {string} dateString - Date string to format
     * @returns {string} - Formatted date
     */
    formatDate(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-AU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
    }
}

// Global instance
window.earlyBirdPriceAdjustment = new EarlyBirdPriceAdjustment();

/**
 * Helper function to check and show price adjustment dialog
 * @param {number} enrollmentId - Enrollment ID
 * @param {Function} onConfirmCallback - Callback after confirmation
 */
window.checkAndShowPriceAdjustment = async function(enrollmentId, onConfirmCallback = null) {
    if (typeof bootstrap === 'undefined') {
        console.warn('[EarlyBird] bootstrap missing, skipping price dialog');
        if (onConfirmCallback) {
            onConfirmCallback({ adjustment_made: false, skipped: 'bootstrap_missing' });
        }
        return false;
    }

    try {
        const csrfInput = document.querySelector('input[name=\"csrfmiddlewaretoken\"]');
        const csrfToken = (csrfInput && csrfInput.value) || (document.cookie.match(/csrftoken=([^;]+)/) || [])[1];

        if (!csrfToken) {
            throw new Error('Missing CSRF token');
        }

        const response = await fetch(`/enrollment/api/check-price-adjustment/${enrollmentId}/`, {
            method: 'GET',
            headers: {
                'X-CSRFToken': csrfToken
            }
        });

        if (!response.ok) {
            throw new Error('Failed to check price adjustment');
        }

        const data = await response.json();

        if (data.needs_adjustment) {
            // Show price adjustment dialog
            window.earlyBirdPriceAdjustment.show(enrollmentId, data, onConfirmCallback);
            return true; // Indicates that dialog was shown
        } else {
            // No adjustment needed, proceed with callback
            if (onConfirmCallback) {
                onConfirmCallback({ adjustment_made: false });
            }
            return false; // Indicates no dialog was needed
        }
    } catch (error) {
        console.error('Error checking price adjustment:', error);
        // On error, proceed without adjustment
        if (onConfirmCallback) {
            onConfirmCallback({ adjustment_made: false, error: error.message });
        }
        return false;
    }
};
}
