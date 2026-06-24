document.addEventListener('DOMContentLoaded', function() {
    // 1. Function to get the CSRF token from cookies (required by Django)
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    const csrftoken = getCookie('csrftoken');

    // 2. Select all "Add to Cart" buttons
    const cartButtons = document.querySelectorAll('.add-to-cart-btn');
    const cartCountSpan = document.getElementById('cart-count');

    cartButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Grab the product ID
            const productId = this.getAttribute('data-product-id');
            const url = `/cart/add/${productId}/`;

            // Optional: Give the user visual feedback that it's adding
            const originalText = this.innerHTML;
            this.innerHTML = "Adding...";
            this.disabled = true;

            // 3. Send the background request to Django
            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Content-Type': 'application/json'
                }
            })
            .then(response => {
                if (response.redirected || response.status === 401 || response.status === 403) {
                    window.location.href = '/accounts/login/';
                    throw new Error('User not logged in');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // 4. Update the cart count in the header
                    if (cartCountSpan) {
                        cartCountSpan.innerText = data.cart_count;
                    }
                    // Reset the button text
                    this.innerHTML = "Added!";
                    setTimeout(() => {
                        this.innerHTML = originalText;
                        this.disabled = false;
                    }, 1500);
                }
            })
            .catch(error => {
                console.log('Cart Error:', error);
                this.innerHTML = originalText;
                this.disabled = false;
            });
        });
    });
});