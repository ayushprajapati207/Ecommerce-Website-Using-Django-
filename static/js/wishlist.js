document.addEventListener('DOMContentLoaded', function() {
    // 1. Django requires a CSRF token for security on POST requests. 
    // This standard function grabs it from your browser cookies.
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

    // 2. Select all heart icons/buttons on the page
    const heartIcons = document.querySelectorAll('.heart-icon, .wishlist-btn');

    heartIcons.forEach(icon => {
        icon.addEventListener('click', function(e) {
            e.preventDefault(); 
            
            // Grab the product ID we embedded in the HTML
            const productId = this.getAttribute('data-product-id');
            const url = `/wishlist/toggle/${productId}/`;

            // 3. Send the background POST request to Django
            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Content-Type': 'application/json'
                }
            })
            .then(response => {
                // If the user isn't logged in, redirect them to the login page
                if (response.redirected || response.status === 401 || response.status === 403) {
                    window.location.href = '/accounts/login/';
                    throw new Error('User not logged in');
                }
                return response.json();
            })
            .then(data => {
                // 4. Update the UI instantly based on Django's response
                if (data.is_added) {
                    this.innerHTML = '&#9829;'; // Solid filled heart
                    this.style.color = '#ff4757'; // Red
                    this.style.borderColor = '#ff4757'; // Red border for detail page button
                } else {
                    this.innerHTML = '&#9825;'; // Empty heart
                    this.style.color = '#ccc';  // Grey
                    this.style.borderColor = '#ccc'; // Grey border
                }
            })
            .catch(error => console.log('Wishlist Error:', error));
        });
    });
});