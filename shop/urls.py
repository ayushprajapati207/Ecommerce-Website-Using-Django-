from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('signup/', views.signup, name='signup'),
    path('wishlist/toggle/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
]