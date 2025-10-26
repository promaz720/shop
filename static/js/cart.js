// Shopping Cart Management
function updateCartCount() {
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');
    const cartCount = document.getElementById('cart-count');
    if (cartCount) {
        cartCount.textContent = cart.length;
    }
}

// Update cart count on page load
document.addEventListener('DOMContentLoaded', updateCartCount);
