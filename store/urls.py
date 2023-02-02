from django.urls import path
from . import views

urlpatterns = [

        path('', views.store, name="store"),
        path('cart/', views.cart, name="cart"),
        path('checkout/', views.checkout, name="checkout"),
        path('update_item/', views.updateItem, name="update_item"),
        path('process_order/', views.processOrder, name="process_order"),
        path('payment_processing/', views.payment_processing, name="payment_processing"),
        path('payment_response_handler/', views.payment_response_handler, name="payment_response_handler"),
        path('api_test/', views.api_test, name="api_test"),



]