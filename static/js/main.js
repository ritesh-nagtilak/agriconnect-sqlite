document.addEventListener('DOMContentLoaded', function() {
    initializeBasicComponents();
    initializeFormHandling();
    console.log('AgriConnect initialized successfully!');
});

function initializeBasicComponents() {
    highlightActiveNavItem();
    initializeBootstrapTooltips();
}

function highlightActiveNavItem() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

function initializeBootstrapTooltips() {
    const tooltipElements = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipElements.forEach(element => {
        new bootstrap.Tooltip(element);
    });
}

function initializeFormHandling() {
    initializeOrderForms();
    initializeReviewForms();
    initializeBasicValidation();
}

function initializeOrderForms() {
    const orderButtons = document.querySelectorAll('.order-btn');
    orderButtons.forEach(button => {
        button.addEventListener('click', function() {
            const productId = this.getAttribute('data-product-id');
            const productName = this.getAttribute('data-product-name');
            const productPrice = parseFloat(this.getAttribute('data-product-price'));
            const maxStock = parseInt(this.getAttribute('data-max-stock'));
            
            showOrderModal(productId, productName, productPrice, maxStock);
        });
    });
}

function showOrderModal(productId, productName, price, maxStock) {
    document.getElementById('productId').value = productId;
    document.getElementById('productName').value = productName;
    document.getElementById('productPrice').value = '₹' + price.toFixed(2);
    document.getElementById('availableStock').value = maxStock + ' units';
    document.getElementById('quantity').max = maxStock;
    document.getElementById('quantity').value = 1;
    
    calculateOrderTotal();
    
    const modal = new bootstrap.Modal(document.getElementById('orderModal'));
    modal.show();
}

function calculateOrderTotal() {
    const quantity = parseInt(document.getElementById('quantity').value) || 0;
    const priceText = document.getElementById('productPrice').value;
    const price = parseFloat(priceText.replace('₹', ''));
    const total = quantity * price;
    
    document.getElementById('totalAmount').value = total.toFixed(2);
}

function placeOrder() {
    const form = document.getElementById('orderForm');
    const formData = new FormData(form);
    
    fetch('/place_order', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage('Order placed successfully!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('orderModal')).hide();
            setTimeout(() => location.reload(), 1000);
        } else {
            showMessage('Error: ' + data.message, 'error');
        }
    })
    .catch(error => {
        showMessage('Error placing order: ' + error.message, 'error');
    });
}

function initializeReviewForms() {
    const reviewButtons = document.querySelectorAll('.review-btn');
    reviewButtons.forEach(button => {
        button.addEventListener('click', function() {
            const orderId = this.getAttribute('data-order-id');
            showReviewModal(orderId);
        });
    });
}

function showReviewModal(orderId) {
    const modal = new bootstrap.Modal(document.getElementById('reviewModal' + orderId));
    modal.show();
}

function submitReview(orderId) {
    const ratingInput = document.querySelector(`input[name="rating-${orderId}"]:checked`);
    const commentInput = document.querySelector(`#comment-${orderId}`);
    
    if (!ratingInput) {
        showMessage('Please select a rating', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('order_id', orderId);
    formData.append('rating', ratingInput.value);
    formData.append('comment', commentInput.value);
    
    fetch('/submit_review', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage('Review submitted successfully!', 'success');
            bootstrap.Modal.getInstance(document.getElementById(`reviewModal${orderId}`)).hide();
            setTimeout(() => location.reload(), 1000);
        } else {
            showMessage('Error: ' + data.message, 'error');
        }
    })
    .catch(error => {
        showMessage('Error submitting review: ' + error.message, 'error');
    });
}

function initializeBasicValidation() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    field.classList.add('is-invalid');
                    isValid = false;
                } else {
                    field.classList.remove('is-invalid');
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                showMessage('Please fill in all required fields', 'error');
            }
        });
    });
}

function updateOrderStatus(orderId, status) {
    if (!confirm('Are you sure you want to ' + status + ' this order?')) {
        return;
    }
    
    const formData = new FormData();
    formData.append('order_id', orderId);
    formData.append('status', status);
    
    fetch('/update_order_status', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage('Order status updated!', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showMessage('Error: ' + data.message, 'error');
        }
    })
    .catch(error => {
        showMessage('Error updating order: ' + error.message, 'error');
    });
}

function showMessage(message, type) {

    let container = document.getElementById('message-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'message-container';
        container.style.position = 'fixed';
        container.style.top = '100px';
        container.style.right = '20px';
        container.style.zIndex = '1050';
        document.body.appendChild(container);
    }
    
    const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
    const messageDiv = document.createElement('div');
    messageDiv.className = `alert ${alertClass} alert-dismissible fade show`;
    messageDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
    `;
    
    container.appendChild(messageDiv);

    setTimeout(() => {
        if (messageDiv.parentElement) {
            messageDiv.remove();
        }
    }, 3000);
}

function formatPrice(price) {
    return '₹' + parseFloat(price).toFixed(2);
}

window.placeOrder = placeOrder;
window.submitReview = submitReview;
window.updateOrderStatus = updateOrderStatus;
window.calculateOrderTotal = calculateOrderTotal;