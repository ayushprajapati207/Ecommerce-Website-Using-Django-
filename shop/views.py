from django.shortcuts import render,get_object_or_404,redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login,logout
from django.db.models import Q
from django.contrib.auth.decorators import login_required 
from django.http import JsonResponse
from .models import Product,CartItem,Cart,Order,OrderItem

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
    product = get_object_or_404(Product, slug=slug, is_available=True)
    
    cart_item = None
    # If the user is logged in, check if this product is already inside their cart
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_item = CartItem.objects.filter(cart=cart, product=product).first()
            
    return render(request, 'shop/product_detail.html', {
        'product': product, 
        'cart_item': cart_item  # Pass this to the template!
    })


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


@login_required
def view_cart(request):
    # Fetch the user's cart (or create an empty one if they somehow don't have one)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # Grab all the items currently sitting in this cart
    items = cart.items.all()
    
    # Calculate the grand total by looping through each item's price
    total_price = sum(item.get_total_price() for item in items)
    
    return render(request, 'shop/cart.html', {
        'items': items, 
        'total_price': total_price
    })


@login_required
def remove_from_cart(request, item_id):
    # Find the specific item, ensuring it actually belongs to the logged-in user's cart
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    
    # Delete it from the database
    cart_item.delete()
    
    # Redirect the user back to their cart page to see the updated total
    return redirect('view_cart')

@login_required
def update_cart_quantity(request, item_id, action):
    # Securely grab the item from the user's cart
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    
    if action == 'add':
        cart_item.quantity += 1
        cart_item.save()
    elif action == 'subtract':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            # If it goes below 1, just remove the item entirely
            cart_item.delete()
            
    # Refresh the cart page to recalculate all totals
    return redirect(request.META.get('HTTP_REFERER', 'view_cart'))


def logout_user(request):
    # This safely destroys the user's session and removes their cookies
    logout(request)
    # Send them back to the shop homepage as a guest
    return redirect('home')


@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    items = cart.items.all()
    
    # If the cart is empty, don't let them checkout
    if not items:
        return redirect('view_cart')
        
    if request.method == 'POST':
        # Grab the data from the HTML form
        name = request.POST.get('full_name')
        address = request.POST.get('shipping_address')
        total_price = sum(item.get_total_price() for item in items)
        
        # 1. Create the permanent Order record
        order = Order.objects.create(
            user=request.user,
            full_name=name,
            shipping_address=address,
            total_price=total_price
        )
        
        # 2. Copy the Cart items into permanent Order items
        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price # Freezes the price
            )
            # Optional: Deduct from actual product stock here
            # item.product.stock -= item.quantity
            # item.product.save()
            
        # 3. Empty the user's cart
        cart.items.all().delete()
        
        # 4. Redirect to a success page
        return redirect('order_success')
        
    return render(request, 'shop/checkout.html', {'items': items})

@login_required
def order_success(request):
    return render(request, 'shop/success.html')