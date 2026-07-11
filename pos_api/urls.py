from django.urls import path, re_path
from .views import (
    RegisterView, LoginView, LogoutView, UserDataView,
    TableListCreateView, TableDetailView,
    OrderListCreateView, OrderDetailView,
    CreateRazorpayOrderView, VerifyRazorpayPaymentView, RazorpayWebhookView
)

urlpatterns = [
    # User / Auth Routes
    path('user/register', RegisterView.as_view(), name='register'),
    path('user/login', LoginView.as_view(), name='login'),
    path('user/logout', LogoutView.as_view(), name='logout'),
    path('user', UserDataView.as_view(), name='user-data'),

    # Table Routes
    path('table/', TableListCreateView.as_view(), name='table-list-create'),
    path('table/<int:id>', TableDetailView.as_view(), name='table-detail'),

    # Order Routes
    path('order/', OrderListCreateView.as_view(), name='order-list-create'),
    path('order/<int:id>', OrderDetailView.as_view(), name='order-detail'),

    # Payment Routes
    path('payment/create-order', CreateRazorpayOrderView.as_view(), name='create-order'),
    # Use regex to support both single and double slash (frontend uses /api/payment//verify-payment)
    re_path(r'^payment//?verify-payment$', VerifyRazorpayPaymentView.as_view(), name='verify-payment'),
    path('payment/webhook-verification', RazorpayWebhookView.as_view(), name='webhook-verification'),
]
