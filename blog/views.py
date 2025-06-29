from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils.http import urlencode
from twilio.twiml.messaging_response import MessagingResponse
from .models import User, Order, Subscription, Payment, PendingPayment
from .forms import UserForm, OrderForm
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Sum
from .pesapal import make_order , get_transaction_status
from .pesapal import get_access_token  
from django.urls import reverse

# PDF generation imports
from django.http import FileResponse
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

def home(request):
    # Example of querying the User model
    all_users = User.objects.all()
    return render(request, 'home.html', {'all': all_users})

def join(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save()

            # ✅ Add 3-day trial subscription if one doesn't exist
            if not Subscription.objects.filter(user=user).exists():
                Subscription.objects.create(
                    user=user,
                    start_date=timezone.now(),
                    end_date=timezone.now() + timedelta(days=3),
                    status='active'
                )

            # ✅ Redirect to WhatsApp with a message
            message = f"Thanks for signing up {user.username}! You have a 3-day free trial. Start placing orders by texting me here."
            encoded_message = urlencode({'text': message})
            whatsapp_number = '14155238886'  # Replace with your Twilio sandbox number

            wa_link = f"https://wa.me/{whatsapp_number}/?{encoded_message}"
            return redirect(wa_link)

        messages.error(request, 'There was an error in your form submission. Please try again.')
    else:
        phone = request.GET.get('phone', '')
        form = UserForm(initial={'phone': phone})

    return render(request, 'join.html', {'form': form})

def order(request):
    # This function would handle order-related logic
    # For now, we can just render a placeholder template
    phone = request.GET.get('phone') or request.POST.get('phone')
    user = User.objects.filter(phone=phone).first()
    
    if not user:
        messages.error(request, "❌ User not found. Please register first.")
        return redirect('join')  # Or wherever you handle new users

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = user  # Set the user using the phone
            order.save()  # order_date is auto-set by auto_now_add
            messages.success(request, "✅ Order placed successfully!")
            return redirect(f'/order_list?phone={phone}')  # or your own confirmation page
    else:
        form = OrderForm()

    return render(request, 'order.html', {'form': form, 'phone': phone})
def order_list(request):
    phone = request.GET.get('phone')
    user = User.objects.filter(phone=phone).first()

    if not user:
        messages.error(request, "❌ No user found with that phone number.")
        return render(request, 'order_list.html', {'paid_orders': [], 'debt_orders': []})

    # Get today's date range
    today = timezone.localdate()
    start_datetime = datetime.combine(today, datetime.min.time(), tzinfo=timezone.get_current_timezone())
    end_datetime = datetime.combine(today, datetime.max.time(), tzinfo=timezone.get_current_timezone())

    # Filter and separate
    todays_orders = Order.objects.filter(user=user, order_date__range=(start_datetime, end_datetime))
    paid_orders = todays_orders.filter(status='paid')
    debt_orders = todays_orders.filter(status='debt')

    # Total amounts
    total_paid = paid_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_debt = debt_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    return render(request, 'order_list.html', {
        'phone': phone,
        'paid_orders': paid_orders,
        'debt_orders': debt_orders,
        'total_paid': total_paid,
        'total_debt': total_debt,
    })

def start_subscription(request):
    phone = request.GET.get('phone')
    user = User.objects.filter(phone=phone).first()

    if not user:
        return HttpResponse("User not found")

    email = user.email
    amount = 20
    callback_url = request.build_absolute_uri(reverse('pesapal_callback'))

    try:
        result = make_order(email, amount, phone, callback_url)
        return redirect(result['redirect_url'])
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}")

def order_receipt(request, order_id):
    order = Order.objects.get(id=order_id)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, bottomup=0)
    textob = c.beginText()
    textob.setTextOrigin(inch, inch)
    textob.setFont("Helvetica", 14)

    lines = [
        "🧾 Order Receipt",
        "-------------------------",
        f"Order ID: {order.id}",
        f"Customer: {order.customer_name}",
        f"Product: {order.product_name}",
        f"Status: {order.status}",
        f"Amount: KES {order.total_amount}",
        f"Date: {order.order_date.strftime('%Y-%m-%d %H:%M')}",
    ]

    for line in lines:
        textob.textLine(line)

    c.drawText(textob)
    c.showPage()
    c.save()
    buf.seek(0)

    return FileResponse(buf, as_attachment=True, filename=f"receipt_order_{order.customer_name}.pdf")

@csrf_exempt
def whatsapp_webhook(request):
    if request.method == 'POST':
        from_number = request.POST.get('From')  # e.g., whatsapp:+2547xxxxxxx
        message_body = request.POST.get('Body').strip().lower()
        
        phone = from_number.replace("whatsapp:", "").replace("+", "")
        user = User.objects.filter(phone=phone).first()

        resp = MessagingResponse()

        if not user:
            resp.message(
                f"👋 Welcome! You're new here.\n"
                f"Please sign up here: https://f0ef-2c0f-fe38-2250-366c-1bbc-faed-2caf-b56c.ngrok-free.app/join?phone={phone}"
            )
        else:
            # ✅ Check user's subscription
            subscription = Subscription.objects.filter(user=user).first()
            now = timezone.now()

            has_access = subscription and subscription.status == 'active' and subscription.end_date > now

            if message_body == 'help':
                if has_access:
                    resp.message(
                        f"Here are your options:"
                        f"\n1. Create Order: https://f0ef-2c0f-fe38-2250-366c-1bbc-faed-2caf-b56c.ngrok-free.app/order?phone={phone}"
                        f"\n2. View Sales: https://f0ef-2c0f-fe38-2250-366c-1bbc-faed-2caf-b56c.ngrok-free.app/order_list?phone={phone}"
                        f"\n3. Pay for Subscription"
                    )
                else:
                    resp.message(
                        "❌ Your subscription is inactive or expired.\n"
                        "Please pay here to continue: https://f0ef-2c0f-fe38-2250-366c-1bbc-faed-2caf-b56c.ngrok-free.app/start_subscription?phone=" + phone
                    )
            else:
                resp.message("👋 Welcome back! Type 'help' for options.")

        return HttpResponse(str(resp), content_type='application/xml')

    return HttpResponse("Invalid request", status=400)

@csrf_exempt
def pesapal_callback(request):
    tracking_id = request.GET.get('OrderTrackingId')
    merchant_reference = request.GET.get('OrderMerchantReference')  # This is now order_id

    if not tracking_id or not merchant_reference:
        return HttpResponse("❌ Missing tracking ID or merchant reference", status=400)

    try:
        payment_info = get_transaction_status(tracking_id)
    except Exception as e:
        return HttpResponse(f"❌ Failed to verify payment: {str(e)}", status=500)

    payment_status = payment_info.get("payment_status_description")
    amount = payment_info.get("amount")

    if payment_status != "Completed":
        return HttpResponse(f"❌ Payment not completed: {payment_status}", status=400)

    # ✅ Find user via PendingPayment
    pending = PendingPayment.objects.filter(order_id=merchant_reference).first()
    if not pending:
        return HttpResponse("❌ No pending payment found", status=404)

    user = pending.user

    # Update subscription
    now = timezone.now()
    sub, _ = Subscription.objects.get_or_create(user=user)
    if sub.end_date and sub.end_date > now:
        sub.end_date += timedelta(days=30)
    else:
        sub.start_date = now
        sub.end_date = now + timedelta(days=30)
    sub.status = 'active'
    sub.save()

    # Log the payment
    Payment.objects.update_or_create(
        tracking_id=tracking_id,
        defaults={
            'user': user,
            'reference': merchant_reference,
            'amount': amount,
            'status': payment_status
        }
    )

    # ✅ Optionally delete the pending payment
    pending.delete()

    return HttpResponse(f"✅ Subscription activated for {user.username}")

@csrf_exempt  # optional if you're already using CSRF token
def mark_as_paid(request):
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        order = get_object_or_404(Order, id=order_id)
        order.status = 'paid'
        order.save()
        messages.success(request, f"✅ Order for {order.customer_name} marked as paid.")
        return redirect(f'/order_list?phone={order.user.phone}')
