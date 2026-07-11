from django.contrib import admin
from django.urls import path, include
from pos_api.views import (
    HomeTemplateView, TablesTemplateView, MenuTemplateView, OrdersTemplateView, DashboardTemplateView,
    AuthTemplateView, AuthLoginView, AuthRegisterView, AuthLogoutView,
    SessionCustomerView, SessionCheckoutView, TableCreateAction,
    ItemCreateAction, ItemEditAction, ItemDeleteAction,
    OrderReportView, OrderJSONView
)

urlpatterns = [
    # Admin Panel
    path('admin/', admin.site.urls),
    
    # Unified HTML Full-Stack routes
    path('', HomeTemplateView.as_view(), name='home_template'),
    path('tables/', TablesTemplateView.as_view(), name='tables_template'),
    path('menu/', MenuTemplateView.as_view(), name='menu_template'),
    path('orders/', OrdersTemplateView.as_view(), name='orders_template'),
    path('dashboard/', DashboardTemplateView.as_view(), name='dashboard_template'),
    
    # Auth HTML targets
    path('auth/', AuthTemplateView.as_view(), name='auth_template'),
    path('auth/login/', AuthLoginView.as_view(), name='auth_login_action'),
    path('auth/register/', AuthRegisterView.as_view(), name='auth_register_action'),
    path('auth/logout/', AuthLogoutView.as_view(), name='auth_logout_action'),

    # Session AJAX targets
    path('session/customer/', SessionCustomerView.as_view(), name='session_customer'),
    path('session/checkout/', SessionCheckoutView.as_view(), name='session_checkout'),
    path('table/create/', TableCreateAction.as_view(), name='table_create_action'),
    
    # Dynamic Item Actions
    path('item/create/', ItemCreateAction.as_view(), name='item_create_action'),
    path('item/edit/', ItemEditAction.as_view(), name='item_edit_action'),
    path('item/delete/', ItemDeleteAction.as_view(), name='item_delete_action'),

    # Reports
    path('report/orders/', OrderReportView.as_view(), name='order_report'),

    # Order JSON (for receipt printing)
    path('order/json/<int:id>/', OrderJSONView.as_view(), name='order_json'),
    
    # REST API endpoints (kept for backwards compatibility/mobile/testing)
    path('api/', include('pos_api.urls')),
]
