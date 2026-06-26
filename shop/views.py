from django.shortcuts import render,get_object_or_404,redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login,logout
from django.db.models import Q
from django.contrib.auth.decorators import login_required 
from django.http import JsonResponse
from .models import Product,Category,CartItem,Cart,Order,OrderItem,Review
from django.core.paginator import Paginator

def home(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(is_available=True)
    
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
        
    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
        
    # --- NEW PAGINATION LOGIC ---
    # Show 6 products per page (you can change this number to whatever you want!)
    paginator = Paginator(products, 6) 
    page_number = request.GET.get('page')
    # This replaces our original 'products' list with just the products for the current page
    products = paginator.get_page(page_number) 
    
    return render(request, 'shop/home.html', {
        'category': category,
        'categories': categories, 
        'products': products, 
        'search_query': query
    })

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_available=True)
    
    # Handle New Review Submission
    if request.method == 'POST' and request.user.is_authenticated:
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        # Save the review to the database
        Review.objects.create(
            product=product,
            user=request.user,
            rating=rating,
            comment=comment
        )
        # Refresh the page to show the new review
        return redirect('product_detail', slug=product.slug)

    # Existing Cart Logic
    cart_item = None
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item = CartItem.objects.filter(cart=cart, product=product).first()
            
    return render(request, 'shop/product_detail.html', {
        'product': product, 
        'cart_item': cart_item
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
        
        # --- NEW INVENTORY CHECK ---
        if product.stock <= 0 or not product.is_available:
            return JsonResponse({'error': 'Product is out of stock'}, status=400)
            
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
        
        if not item_created:
            # --- PREVENT EXCEEDING STOCK ---
            if cart_item.quantity < product.stock:
                cart_item.quantity += 1
                cart_item.save()
            else:
                return JsonResponse({'error': 'Not enough stock available'}, status=400)
                
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
        # --- NEW INVENTORY CHECK ---
        # Only increase the quantity if it's less than what you actually have in stock
        if cart_item.quantity < cart_item.product.stock:
            cart_item.quantity += 1
            cart_item.save()
        # (If they hit the limit, it just ignores the click and reloads the page)
            
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
                price=item.product.price
            )
            
            # --- NEW INVENTORY LOGIC ---
            # Deduct the purchased amount from the main product stock
            item.product.stock -= item.quantity
            
            # If the stock hits zero, automatically mark it as unavailable
            if item.product.stock <= 0:
                item.product.stock = 0
                item.product.is_available = False
                
            item.product.save()
            
        # 3. Empty the user's cart
        cart.items.all().delete()
        
        # 4. Redirect to a success page
        return redirect('order_success')
        
    return render(request, 'shop/checkout.html', {'items': items})

@login_required
def order_success(request):
    return render(request, 'shop/success.html')


@login_required
def profile(request):
    # Fetch all orders for this user, sorted by newest first (using the minus sign)
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'shop/profile.html', {'orders': orders})

@login_required
def wishlist_page(request):
    # Fetch all products where the current user is in the wishlist relationship
    wishlist_products = Product.objects.filter(users_wishlist=request.user)
    
    return render(request, 'shop/wishlist.html', {'products': wishlist_products})