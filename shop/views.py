from django.shortcuts import render,get_object_or_404,redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required 
from django.http import JsonResponse
from .models import Product

def home(request):
    # Fetch all products that are currently in stock/available
    products = Product.objects.filter(is_available=True)
    
    # Pass those products to a template we will create in the next step
    return render(request, 'shop/home.html', {'products': products})

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

