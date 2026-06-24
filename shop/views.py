from django.shortcuts import render,get_object_or_404,redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.db.models import Q
from django.contrib.auth.decorators import login_required 
from django.http import JsonResponse
from .models import Product,Category,CartItem,Cart

def home(request):
    # Get the search term from the URL (e.g., ?q=shirt)
    query = request.GET.get('q')
    
    # Start with all available products
    products = Product.objects.filter(is_available=True)
    
    # If the user typed something in the search bar, filter the products
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    
    # Pass the products and the query back to the template
    return render(request, 'shop/home.html', {'products': products, 'search_query': query})

def product_detail(request, slug):
    # Fetch the exact product using its unique slug
    product = get_object_or_404(Product, slug=slug, is_available=True)
    return render(request, 'shop/product_detail.html', {'product': product})


def signup(request):
    # If the user clicks the "Submit" button on the form
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()         # Create and save the new user
            login(request, user)       # Automatically log them in right after
            return redirect('home')    # Send them to the shop homepage
    else:
        # If the user is just opening the page, show a blank form
        form = UserCreationForm()
        
    return render(request, 'registration/signup.html', {'form': form})


@login_required # Forces the user to be logged in to use this
def toggle_wishlist(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        
        # If the user already has it in their wishlist, remove it
        if request.user in product.users_wishlist.all():
            product.users_wishlist.remove(request.user)
            is_added = False
        # Otherwise, add it
        else:
            product.users_wishlist.add(request.user)
            is_added = True
            
        # Send a JSON response back to the browser
        return JsonResponse({'is_added': is_added})
        
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def add_to_cart(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        
        # Get the user's cart, or create a new one if it doesn't exist
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Check if this exact product is already in their cart
        cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
        
        if not item_created:
            # If it was already in the cart, just add 1 to the quantity
            cart_item.quantity += 1
            cart_item.save()
            
        # Calculate the total number of unique items in the cart to update the header
        cart_count = cart.items.count()
        
        return JsonResponse({'success': True, 'cart_count': cart_count})
        
    return JsonResponse({'error': 'Invalid request'}, status=400)
