import os
import hmac
import hashlib
import json
import datetime
import jwt
from django.conf import settings
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View
from django.http import JsonResponse, HttpResponseRedirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
import razorpay

from .models import User, Table, Order, Payment, MenuItem
from .serializers import UserSerializer, TableSerializer, OrderSerializer, PaymentSerializer
from .menus import MENUS, POPULAR_DISHES


# ==========================================
# API CONTROLLERS (REST Framework API Views)
# ==========================================

# Helper to generate JWT token (matching original API)
def generate_token(user):
    expiration = datetime.datetime.utcnow() + datetime.timedelta(days=1)
    payload = {
        '_id': user.id,
        'exp': expiration
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        name = request.data.get('name')
        phone = request.data.get('phone')
        email = request.data.get('email')
        password = request.data.get('password')
        role = request.data.get('role')

        if not all([name, phone, email, password, role]):
            return Response({"success": False, "message": "All fields are required!"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({"success": False, "message": "User already exist!"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.create_user(
                email=email,
                name=name,
                phone=phone,
                role=role,
                password=password
            )
            serializer = UserSerializer(user)
            return Response({
                "success": True,
                "message": "New user created!",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({"success": False, "message": "All fields are required!"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"success": False, "message": "Invalid Credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            return Response({"success": False, "message": "Invalid Credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        token = generate_token(user)

        serializer = UserSerializer(user)
        response = Response({
            "success": True,
            "message": "User login successfully!",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

        response.set_cookie(
            'accessToken',
            token,
            max_age=1000 * 60 * 60 * 24 * 30 // 1000,
            httponly=True,
            samesite='None',
            secure=True
        )
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = Response({
            "success": True,
            "message": "User logout successfully!"
        }, status=status.HTTP_200_OK)
        
        response.delete_cookie('accessToken')
        return response


class UserDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response({
            "success": True,
            "data": serializer.data
        }, status=status.HTTP_200_OK)


class TableListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tables = Table.objects.all()
        serializer = TableSerializer(tables, many=True)
        return Response({
            "success": True,
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        tableNo = request.data.get('tableNo')
        seats = request.data.get('seats')

        if not tableNo:
            return Response({"success": False, "message": "Please provide table No!"}, status=status.HTTP_400_BAD_REQUEST)

        if Table.objects.filter(tableNo=tableNo).exists():
            return Response({"success": False, "message": "Table already exist!"}, status=status.HTTP_400_BAD_REQUEST)

        table = Table.objects.create(tableNo=tableNo, seats=seats)
        serializer = TableSerializer(table)
        return Response({
            "success": True,
            "message": "Table added!",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)


class TableDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, id):
        try:
            table = Table.objects.get(id=id)
        except Table.DoesNotExist:
            return Response({"success": False, "message": "Table not found!"}, status=status.HTTP_404_NOT_FOUND)

        status_val = request.data.get('status')
        order_id = request.data.get('orderId')

        if status_val is not None:
            table.status = status_val

        if order_id is not None:
            if order_id == "" or order_id is None:
                table.currentOrder = None
            else:
                try:
                    order = Order.objects.get(id=order_id)
                    table.currentOrder = order
                except Order.DoesNotExist:
                    return Response({"success": False, "message": "Order not found!"}, status=status.HTTP_404_NOT_FOUND)

        table.save()
        serializer = TableSerializer(table)
        return Response({
            "success": True,
            "message": "Table updated!",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


class OrderListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.all().select_related('table')
        serializer = OrderSerializer(orders, many=True)
        return Response({
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = OrderSerializer(data=request.data)
        if serializer.is_valid():
            order = serializer.save()
            return Response({
                "success": True,
                "message": "Order created!",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({"success": False, "message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        try:
            order = Order.objects.get(id=id)
            serializer = OrderSerializer(order)
            return Response({
                "success": True,
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        except Order.DoesNotExist:
            return Response({"success": False, "message": "Order not found!"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, id):
        try:
            order = Order.objects.get(id=id)
        except Order.DoesNotExist:
            return Response({"success": False, "message": "Order not found!"}, status=status.HTTP_404_NOT_FOUND)

        order_status = request.data.get('orderStatus')
        if order_status is not None:
            order.orderStatus = order_status
            
            # If status becomes Completed or Cancelled, we free up the occupied table
            if order_status in ['Completed', 'Cancelled'] and order.table:
                tbl = order.table
                tbl.status = 'Available'
                tbl.currentOrder = None
                tbl.save()
                
            order.save()

        serializer = OrderSerializer(order)
        return Response({
            "success": True,
            "message": "Order updated",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


class CreateRazorpayOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        key_id = os.getenv('RAZORPAY_KEY_ID')
        secret_key = os.getenv('RAZORPAY_KEY_SECRET')

        if not key_id or not secret_key:
            return Response({
                "success": False, 
                "message": "Razorpay credentials not configured!"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            client = razorpay.Client(auth=(key_id, secret_key))
            amount = request.data.get('amount')
            if not amount:
                return Response({"success": False, "message": "Please provide amount!"}, status=status.HTTP_400_BAD_REQUEST)

            options = {
                "amount": int(float(amount) * 100),
                "currency": "INR",
                "receipt": f"receipt_{int(timezone.now().timestamp())}"
            }
            order = client.order.create(data=options)
            
            # Inject key_id into output so client script knows it
            order['key_id'] = key_id
            return Response({"success": True, "order": order}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyRazorpayPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        secret_key = os.getenv('RAZORPAY_KEY_SECRET')
        if not secret_key:
            return Response({
                "success": False, 
                "message": "Razorpay credentials not configured!"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_signature = request.data.get('razorpay_signature')

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return Response({"success": False, "message": "Missing verification parameters!"}, status=status.HTTP_400_BAD_REQUEST)

        msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode('utf-8')
        expected_signature = hmac.new(
            secret_key.encode('utf-8'),
            msg,
            hashlib.sha256
        ).hexdigest()

        if expected_signature == razorpay_signature:
            return Response({"success": True, "message": "Payment verified successfully!"}, status=status.HTTP_200_OK)
        else:
            return Response({"success": False, "message": "Payment verification failed!"}, status=status.HTTP_400_BAD_REQUEST)


class RazorpayWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        secret = os.getenv('RAZORPAY_WEBHOOK_SECRET')
        signature = request.headers.get("X-Razorpay-Signature")

        if not secret or not signature:
            return Response({"success": False, "message": "Webhook secret or signature missing!"}, status=status.HTTP_400_BAD_REQUEST)

        body = request.body

        expected_signature = hmac.new(
            secret.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()

        if expected_signature == signature:
            try:
                data = json.loads(body.decode('utf-8'))
                if data.get('event') == 'payment.captured':
                    payment_entity = data['payload']['payment']['entity']
                    
                    Payment.objects.create(
                        paymentId=payment_entity.get('id'),
                        orderId=payment_entity.get('order_id'),
                        amount=float(payment_entity.get('amount')) / 100.0,
                        currency=payment_entity.get('currency'),
                        status=payment_entity.get('status'),
                        method=payment_entity.get('method'),
                        email=payment_entity.get('email'),
                        contact=payment_entity.get('contact'),
                        createdAt=timezone.make_aware(datetime.datetime.fromtimestamp(payment_entity.get('created_at')))
                    )
                return Response({"success": True}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"success": False, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({"success": False, "message": "Invalid Signature!"}, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# DJANGO TEMPLATES VIEWS (Full-Stack Render)
# ==========================================

class LoginRequiredMixin:
    @method_decorator(login_required(login_url='/auth/'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class HomeTemplateView(LoginRequiredMixin, View):
    def get(self, request):
        completed_orders = Order.objects.filter(orderStatus='Completed')
        total_earnings = sum(float(o.bills.get('totalWithTax', 0)) for o in completed_orders)
        
        in_progress_count = Order.objects.filter(orderStatus__in=['Pending', 'Preparing']).count()
        recent_orders = Order.objects.all().order_by('-orderDate')[:10]

        context = {
            'total_earnings': total_earnings,
            'in_progress_count': in_progress_count,
            'orders': recent_orders,
            'popular_dishes': POPULAR_DISHES,
        }
        return render(request, 'home.html', context)


class TablesTemplateView(LoginRequiredMixin, View):
    def get(self, request):
        tables = Table.objects.all().order_by('tableNo')
        has_customer = 'customer' in request.session

        context = {
            'tables': tables,
            'has_customer': has_customer,
        }
        return render(request, 'tables.html', context)


def get_dynamic_menus():
    # If database is empty, seed it with static MENUS
    if MenuItem.objects.count() == 0:
        for cat in MENUS:
            for item in cat['items']:
                MenuItem.objects.create(
                    name=item['name'],
                    price=item['price'],
                    category=cat['name'],
                    icon=cat['icon'],
                    bgColor=cat.get('bgColor', '#5b45b0')
                )
    
    # Query database and group by category
    db_items = MenuItem.objects.all().order_by('id')
    categories_dict = {}
    for item in db_items:
        cat_name = item.category
        if cat_name not in categories_dict:
            categories_dict[cat_name] = {
                'id': len(categories_dict) + 1,
                'name': cat_name,
                'icon': item.icon,
                'bgColor': item.bgColor,
                'items': []
            }
        categories_dict[cat_name]['items'].append({
            'id': item.id,
            'name': item.name,
            'price': item.price
        })
    
    return list(categories_dict.values())


class MenuTemplateView(LoginRequiredMixin, View):
    def get(self, request):
        customer = request.session.get('customer')
        if not customer:
            return redirect('/tables/')

        # Capture URL assignments from table redirection
        table_id = request.GET.get('table_id')
        table_no = request.GET.get('table_no')
        if table_id and table_no:
            customer['table_id'] = table_id
            customer['table_no'] = table_no
            request.session['customer'] = customer

        context = {
            'customer': customer,
            'menus_json': json.dumps(get_dynamic_menus()),
        }
        return render(request, 'menu.html', context)


class OrdersTemplateView(LoginRequiredMixin, View):
    def get(self, request):
        orders = Order.objects.all().order_by('-orderDate')
        context = {
            'orders': orders,
        }
        return render(request, 'orders.html', context)


class DashboardTemplateView(LoginRequiredMixin, View):
    def get(self, request):
        all_orders = Order.objects.all()
        completed = all_orders.filter(orderStatus='Completed')
        
        revenue = sum(float(o.bills.get('totalWithTax', 0)) for o in completed)
        active_orders = all_orders.filter(orderStatus__in=['Pending', 'Preparing']).count()
        customer_count = all_orders.count()
        avg_order_size = revenue / customer_count if customer_count > 0 else 0.0

        context = {
            'revenue': revenue,
            'active_orders': active_orders,
            'customer_count': customer_count,
            'avg_order_size': avg_order_size,
            'tables_count': Table.objects.count(),
            'booked_tables': Table.objects.filter(status='Booked').count(),
            'orders': all_orders.order_by('-orderDate'),
            'payments': Payment.objects.all().order_by('-id'),
            'menus_json': json.dumps(get_dynamic_menus()),
        }
        return render(request, 'dashboard.html', context)


# ==========================================
# AUTHENTICATION TEMPLATE VIEWS
# ==========================================

class AuthTemplateView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('/')
        return render(request, 'auth.html')


class AuthLoginView(View):
    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not email or not password:
            return render(request, 'auth.html', {"error": "All fields are required!"})

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return render(request, 'auth.html', {"error": "Invalid Credentials"})

        if not user.check_password(password):
            return render(request, 'auth.html', {"error": "Invalid Credentials"})

        django_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        
        # Also set the JWT token cookie to maintain full REST API compatibility!
        response = redirect('/')
        token = generate_token(user)
        response.set_cookie(
            'accessToken',
            token,
            max_age=1000 * 60 * 60 * 24 * 30 // 1000,
            httponly=True,
            samesite='None',
            secure=True
        )
        return response


class AuthRegisterView(View):
    def post(self, request):
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        role = request.POST.get('role', 'Waiter')

        if not all([name, email, phone, password, role]):
            return render(request, 'auth.html', {"error": "All fields are required!"})

        if User.objects.filter(email=email).exists():
            return render(request, 'auth.html', {"error": "User already exist!"})

        try:
            user = User.objects.create_user(
                email=email,
                name=name,
                phone=phone,
                role=role,
                password=password
            )
            django_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            response = redirect('/')
            token = generate_token(user)
            response.set_cookie(
                'accessToken',
                token,
                max_age=1000 * 60 * 60 * 24 * 30 // 1000,
                httponly=True,
                samesite='None',
                secure=True
            )
            return response
        except Exception as e:
            return render(request, 'auth.html', {"error": str(e)})


class AuthLogoutView(View):
    def post(self, request):
        django_logout(request)
        response = redirect('/auth/')
        response.delete_cookie('accessToken')
        return response


# ==========================================
# SESSION / AJAX ENDPOINTS
# ==========================================

class SessionCustomerView(View):
    def post(self, request):
        try:
            data = json.loads(request.body.decode('utf-8'))
            name = data.get('name', 'Guest') or 'Guest'
            phone = data.get('phone', '0000000000') or '0000000000'
            guests = data.get('guests', 1) or 1

            request.session['customer'] = {
                'name': name,
                'phone': phone,
                'guests': guests
            }
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})


class SessionCheckoutView(View):
    def post(self, request):
        try:
            data = json.loads(request.body.decode('utf-8'))
            
            table_id = data.get('table')
            table = None
            if table_id:
                try:
                    table = Table.objects.get(id=table_id)
                except Table.DoesNotExist:
                    return JsonResponse({"success": False, "message": "Selected table not found!"})

            # Create Order record
            order = Order.objects.create(
                customerDetails=data.get('customerDetails'),
                orderStatus=data.get('orderStatus', 'Pending'),
                bills=data.get('bills'),
                items=data.get('items', []),
                table=table,
                paymentMethod=data.get('paymentMethod'),
                paymentData=data.get('paymentData')
            )

            # Mark Table as Booked and associate order
            if table:
                table.status = 'Booked'
                table.currentOrder = order
                table.save()

            # Create payment record in DB if cash/card checkout completed
            if data.get('paymentMethod') in ['Cash', 'Card']:
                Payment.objects.create(
                    paymentId=f"CASH_{int(timezone.now().timestamp())}",
                    orderId=str(order.id),
                    amount=float(order.bills.get('totalWithTax')),
                    currency="INR",
                    status="captured",
                    method=data.get('paymentMethod').lower(),
                    email=request.user.email,
                    contact=order.customerDetails.get('phone'),
                    createdAt=timezone.now()
                )

            # Clear session cart and customer information
            if 'customer' in request.session:
                del request.session['customer']

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})


class TableCreateAction(View):
    def post(self, request):
        tableNo = request.POST.get('tableNo')
        seats = request.POST.get('seats')
        redirect_param = request.GET.get('redirect', 'tables')

        if not tableNo or not seats:
            return redirect('/tables/')

        try:
            if not Table.objects.filter(tableNo=tableNo).exists():
                Table.objects.create(tableNo=tableNo, seats=seats)
        except Exception as e:
            pass

        if redirect_param == 'dashboard':
            return redirect('/dashboard/')
        return redirect('/tables/')


class ItemCreateAction(View):
    def post(self, request):
        try:
            data = json.loads(request.body.decode('utf-8'))
            name = data.get('name')
            price = data.get('price')
            category = data.get('category', 'Starters')
            icon = data.get('icon', '🍛')
        except Exception:
            name = request.POST.get('name')
            price = request.POST.get('price')
            category = request.POST.get('category', 'Starters')
            icon = request.POST.get('icon', '🍛')

        if not name or not price:
            return JsonResponse({"success": False, "message": "Name and price are required!"})

        try:
            MenuItem.objects.create(
                name=name,
                price=float(price),
                category=category,
                icon=icon
            )
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})


class ItemEditAction(View):
    def post(self, request):
        try:
            data = json.loads(request.body.decode('utf-8'))
            item_id = data.get('id')
            name = data.get('name')
            price = data.get('price')
            category = data.get('category')
        except Exception:
            item_id = request.POST.get('id')
            name = request.POST.get('name')
            price = request.POST.get('price')
            category = request.POST.get('category')

        if not item_id or not name or not price:
            return JsonResponse({"success": False, "message": "Item ID, Name, and Price are required!"})

        try:
            item = MenuItem.objects.get(id=item_id)
            item.name = name
            item.price = float(price)
            if category:
                item.category = category
            item.save()
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})


class ItemDeleteAction(View):
    def post(self, request):
        try:
            data = json.loads(request.body.decode('utf-8'))
            item_id = data.get('id')
        except Exception:
            item_id = request.POST.get('id')

        if not item_id:
            return JsonResponse({"success": False, "message": "Item ID is required!"})

        try:
            item = MenuItem.objects.get(id=item_id)
            item.delete()
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})


class OrderReportView(LoginRequiredMixin, View):
    """AJAX endpoint: returns order report grouped by day for a given date range."""
    def get(self, request):
        from_date_str = request.GET.get('from_date')
        to_date_str = request.GET.get('to_date')
        preset = request.GET.get('preset')  # 'today', 'week', 'month'

        today = datetime.date.today()

        if preset == 'today':
            from_date = today
            to_date = today
        elif preset == 'week':
            from_date = today - datetime.timedelta(days=6)
            to_date = today
        elif preset == 'month':
            from_date = today.replace(day=1)
            to_date = today
        else:
            try:
                from_date = datetime.datetime.strptime(from_date_str, '%Y-%m-%d').date() if from_date_str else today
                to_date = datetime.datetime.strptime(to_date_str, '%Y-%m-%d').date() if to_date_str else today
            except (ValueError, TypeError):
                return JsonResponse({"success": False, "message": "Invalid date format. Use YYYY-MM-DD."})

        # Include the full to_date day (up to midnight of the next day)
        qs = Order.objects.filter(
            orderDate__date__gte=from_date,
            orderDate__date__lte=to_date
        ).order_by('orderDate')

        # Build per-day breakdown
        from collections import defaultdict
        day_map = defaultdict(lambda: {"orders": 0, "revenue": 0.0, "completed": 0, "cancelled": 0, "pending": 0})

        for order in qs:
            day_str = order.orderDate.strftime('%Y-%m-%d')
            day_map[day_str]["orders"] += 1
            amount = float(order.bills.get('totalWithTax', 0)) if order.bills else 0.0
            if order.orderStatus == 'Completed':
                day_map[day_str]["revenue"] += amount
                day_map[day_str]["completed"] += 1
            elif order.orderStatus == 'Cancelled':
                day_map[day_str]["cancelled"] += 1
            else:
                day_map[day_str]["pending"] += 1

        rows = []
        current = from_date
        while current <= to_date:
            ds = current.strftime('%Y-%m-%d')
            d = day_map.get(ds, {"orders": 0, "revenue": 0.0, "completed": 0, "cancelled": 0, "pending": 0})
            rows.append({
                "date": ds,
                "display_date": current.strftime('%d %b %Y'),
                "orders": d["orders"],
                "completed": d["completed"],
                "cancelled": d["cancelled"],
                "pending": d["pending"],
                "revenue": round(d["revenue"], 2),
            })
            current += datetime.timedelta(days=1)

        total_orders = sum(r["orders"] for r in rows)
        total_revenue = round(sum(r["revenue"] for r in rows), 2)
        total_completed = sum(r["completed"] for r in rows)
        total_cancelled = sum(r["cancelled"] for r in rows)

        return JsonResponse({
            "success": True,
            "from_date": from_date.strftime('%Y-%m-%d'),
            "to_date": to_date.strftime('%Y-%m-%d'),
            "rows": rows,
            "summary": {
                "total_orders": total_orders,
                "total_completed": total_completed,
                "total_cancelled": total_cancelled,
                "total_revenue": total_revenue,
            }
        })


class OrderJSONView(LoginRequiredMixin, View):
    """Returns a single order's full data as clean JSON for the print receipt on the orders page."""
    def get(self, request, id):
        try:
            order = Order.objects.select_related('table').get(id=id)
        except Order.DoesNotExist:
            return JsonResponse({"success": False, "message": "Order not found."}, status=404)

        bills = order.bills or {}
        customer = order.customerDetails or {}

        return JsonResponse({
            "success": True,
            "id": order.id,
            "customer": customer.get("name", "Guest"),
            "phone": customer.get("phone", "N/A"),
            "guests": customer.get("guests", 1),
            "table": str(order.table.tableNo) if order.table else "N/A",
            "date": order.orderDate.strftime("%d %b %Y %I:%M %p"),
            "status": order.orderStatus,
            "payment": order.paymentMethod or "N/A",
            "items": order.items or [],
            "bills": {
                "total": float(bills.get("total", 0)),
                "tax": float(bills.get("tax", 0)),
                "totalWithTax": float(bills.get("totalWithTax", 0)),
            }
        })

class OrderDeleteView(LoginRequiredMixin, View):
    def delete(self, request, id):
        try:
            order = Order.objects.get(id=id)
            # Free up table if needed
            if order.table and order.table.currentOrder_id == order.id:
                order.table.currentOrder = None
                order.table.status = "Available"
                order.table.save()
            order.delete()
            return JsonResponse({'success': True, 'message': 'Order deleted successfully'})
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Order not found'}, status=404)

class OrderUpdateView(LoginRequiredMixin, View):
    def post(self, request, id):
        try:
            order = Order.objects.get(id=id)
            data = json.loads(request.body)
            items = data.get('items', [])
            table_id = data.get('table')
            payment_method = data.get('paymentMethod', 'Cash')

            if not items:
                return JsonResponse({'success': False, 'message': 'Cart is empty'}, status=400)

            # Recalculate totals
            subtotal = sum(float(item['total']) for item in items)
            tax = subtotal * 0.18
            total_with_tax = subtotal + tax

            order.items = items
            order.bills = {
                'total': subtotal,
                'tax': tax,
                'totalWithTax': total_with_tax
            }
            order.paymentMethod = payment_method

            # Update Table mapping if changed
            if table_id:
                try:
                    table = Table.objects.get(id=table_id)
                    order.table = table
                    table.status = "Occupied"
                    table.currentOrder = order
                    table.save()
                except Table.DoesNotExist:
                    pass

            order.save()
            return JsonResponse({'success': True, 'message': 'Order updated successfully'})
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Order not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
