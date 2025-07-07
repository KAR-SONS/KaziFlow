from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils.http import urlencode
from twilio.twiml.messaging_response import MessagingResponse
from .models import User, Order, Subscription, Payment, PendingPayment, OrderItem
from .forms import UserForm, OrderForm, OrderItemFormSet
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Sum
from .pesapal import make_order , get_transaction_status
from .pesapal import get_access_token  
from django.urls import reverse
from django.utils.timezone import make_aware
import logging

logger = logging.getLogger(__name__)

# PDF generation imports
from django.http import FileResponse
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

def landing(request):
    # Render the landing page template
    return render(request, 'landing.html')
def home(request):
    # Example of querying the User model
    all_users = User.objects.all()
    return render(request, 'home.html', {'all': all_users})

def join(request):
    ref = request.GET.get('ref')
    phone = request.GET.get('phone', '')

    # Get the referrer user if it exists and is valid
    referrer = None
    if ref:
        referrer = User.objects.filter(username=ref, is_referrer=True).first()

    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.referrer = referrer  # ✅ Set referrer if available
            user.save()

            # ✅ Add 3-day trial
            if not Subscription.objects.filter(user=user).exists():
                Subscription.objects.create(
                    user=user,
                    start_date=timezone.now(),
                    end_date=timezone.now() + timedelta(days=3),
                    status='active'
                )

            # ✅ WhatsApp message
            message = (
                f"Thanks for signing up {user.username}! You have a 3-day free trial. "
                "You can create Orders, filter for weekly/monthly sales, and generate receipts. "
                "Start placing orders by texting me here."
            )
            encoded_message = urlencode({'text': message})
            whatsapp_number = '15557906367'

            wa_link = f"https://wa.me/{whatsapp_number}/?{encoded_message}"
            return redirect(wa_link)

        messages.error(request, 'There was an error in your form submission. Please try again.')
    else:
        form = UserForm(initial={'phone': phone})

    return render(request, 'join.html', {'form': form})

def referral_report(request, referrer_id):
    referrer = get_object_or_404(User, id=referrer_id)

    # Get all users referred by this referrer
    referrals = referrer.referrals.all()

    # Annotate with subscription status
    referral_data = []
    for user in referrals:
        subscription = Subscription.objects.filter(user=user, status='active').first()
        referral_data.append({
            'user': user,
            'has_paid': bool(subscription)
        })

    return render(request, 'referral_report.html', {
        'referrer': referrer,
        'referral_data': referral_data
    })

def referrer_links(request, referrer_id):
    referrer = get_object_or_404(User, id=referrer_id)

    referrals_list_link = f"https://kaziflow.onrender.com/referrals/{referrer.id}"
    ref_code = referrer.username

    # Direct link that user should click to start WhatsApp conversation
    ref_message = f"join ref={ref_code}"
    whatsapp_direct_link = f"https://wa.me/15557906367?{urlencode({'text': ref_message})}"

    # Optional: prewritten WhatsApp share message with friendly text
    message = (
        "👋 Join KaziFlow and manage your sales with ease.\n"
        "To start your free trial, just message our bot here 👇\n\n"
        f"{whatsapp_direct_link}"
    )
    whatsapp_share_link = f"https://wa.me/?{urlencode({'text': message})}"

    return render(request, 'referrer_links.html', {
        'referrer': referrer,
        'whatsapp_direct_link': whatsapp_direct_link,
        'whatsapp_share_link': whatsapp_share_link,
        'referrals_list_link': referrals_list_link
    })


# views.py
def order(request):
    phone = request.GET.get('phone') or request.POST.get('phone')
    user = User.objects.filter(phone=phone).first()

    if not user:
        messages.error(request, "❌ User not found. Please register first.")
        return redirect('join')

    if request.method == 'POST':
        form = OrderForm(request.POST)
        formset = OrderItemFormSet(request.POST, queryset=OrderItem.objects.none())

        if form.is_valid() and formset.is_valid():
            order = form.save(commit=False)
            order.user = user
            order.status = request.POST.get('status')

            total = 0
            for item_form in formset:
                item = item_form.save(commit=False)
                item.order = order
                total += item.price * item.quantity
            order.total_amount = total

            order.save()  # ✅ Save only AFTER total_amount is set

            for item_form in formset:
                item = item_form.save(commit=False)
                item.order = order
                item.save()

            return redirect(f"/order_list?phone={phone}")

    else:
        form = OrderForm()
        formset = OrderItemFormSet(queryset=OrderItem.objects.none())

    return render(request, 'order.html', {
        'form': form,
        'formset': formset,
        'phone': phone
    })

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
    amount = 800
    callback_url = request.build_absolute_uri(reverse('pesapal_callback'))

    try:
        result = make_order(email, amount, phone, callback_url)
        return redirect(result['redirect_url'])
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}")

from reportlab.lib.pagesizes import A5

def order_receipt(request, order_id):
    order = Order.objects.get(id=order_id)
    items = OrderItem.objects.filter(order=order)

    # Format product details like "Spanner (1), Brake Fluid (2)"
    product_details = ", ".join(f"{item.product_name} ({item.quantity})" for item in items)

    buf = io.BytesIO()
    page_width, page_height = A5
    c = canvas.Canvas(buf, pagesize=A5, bottomup=0)

    margin = 30
    c.setStrokeColorRGB(0.2, 0.2, 0.2)
    c.setLineWidth(1.2)
    c.rect(margin, margin, page_width - 2 * margin, page_height - 2 * margin)

    textob = c.beginText()
    textob.setFont("Helvetica", 7)
    start_y = margin + 40
    textob.setTextOrigin(margin + 7, start_y)

    def center_line(text, font_size=7, bold=False):
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, font_size)
        text_width = c.stringWidth(text, font, font_size)
        x = (page_width - text_width) / 2
        y = textob.getY()
        c.drawString(x, y, text)
        textob.moveCursor(0, 6)

    center_line("🧾 KaziFlow - Order Receipt", 12, bold=True)
    center_line("-----------------------------", 10)

    details = [
        f"Order ID: {order.id}",
        f"Customer: {order.customer_name}",
        f"Products: {product_details}",
        f"Status: {order.status}",
        f"Amount: KES {order.total_amount}",
        f"Date: {order.order_date.strftime('%Y-%m-%d %H:%M')}",
        "",
        f"Sold by: {order.user.username}"
    ]

    for line in details:
        is_bold = line.startswith("Sold by:")
        center_line(line, 10, bold=is_bold)

    c.drawText(textob)
    c.showPage()
    c.save()
    buf.seek(0)

    return FileResponse(buf, as_attachment=True, filename=f"receipt_order_{order.customer_name}.pdf")
def filter_orders(request):
    phone = request.GET.get('phone')
    user = User.objects.filter(phone=phone).first()

    if not user:
        messages.error(request, "❌ No user found with that phone number.")
        return redirect('order_list')

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if not start_date or not end_date:
        messages.error(request, "❌ Please provide both start and end dates.")
        return redirect(f'/order_list?phone={phone}')

    try:
        start_datetime = make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
        end_datetime = make_aware(datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))  # include end day
    except ValueError:
        messages.error(request, "❌ Invalid date format. Use YYYY-MM-DD.")
        return redirect(f'/order_list?phone={phone}')

    orders = Order.objects.filter(user=user, order_date__range=(start_datetime, end_datetime))
    paid_orders = orders.filter(status='paid')
    debt_orders = orders.filter(status='debt')

    total_paid = paid_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_debt = debt_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    return render(request, 'order_list.html', {
        'phone': phone,
        'paid_orders': paid_orders,
        'debt_orders': debt_orders,
        'total_paid': total_paid,
        'total_debt': total_debt,
        'filtered': True,
        'start_date': start_date,
        'end_date': end_date,
    })
@csrf_exempt
def whatsapp_webhook(request):
    if request.method != 'POST':
        return HttpResponse("Invalid request", status=400)

    logger.warning("RAW POST: %s", request.POST.dict())

    from_number = request.POST.get('From')
    message_body = request.POST.get('Body', '').strip().lower()

    if not from_number or not message_body:
        return HttpResponse("❌ Missing data", status=400)

    phone = from_number.replace("whatsapp:", "").replace("+", "")
    resp = MessagingResponse()

    # Check if user already exists
    user = User.objects.filter(phone=phone).first()

    # 🔰 First-time user must type 'kaziflow' to begin
    if not user:
        if message_body == 'kaziflow' or message_body.startswith("join"):
            ref_code = None
            if "ref=" in message_body:
                for part in message_body.split():
                    if part.startswith("ref="):
                        ref_code = part.split("=")[1]

            referrer = User.objects.filter(username=ref_code, is_referrer=True).first() if ref_code else None

            # Create user account
            user = User.objects.create(
                phone=phone,
                username=f"user_{phone[-4:]}",
                email=f"{phone}@kaziflow.com",
                password="defaultpass",
                referrer=referrer
            )

            # Create trial subscription
            Subscription.objects.create(
                user=user,
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=3),
                status='active'
            )

            ref_text = f" referred by {referrer.username}" if referrer else ""
            resp.message(f"🎉 Welcome to KaziFlow! You’ve been signed up for a 3-day trial{ref_text}. Type *help* to get started.")
        else:
            # Guide them to type the correct message
            resp.message("👋 Welcome to KaziFlow!\nTo begin, please type *kaziflow* to sign up.")
        return HttpResponse(str(resp), content_type='application/xml')

    # ✅ At this point, user exists
    subscription = Subscription.objects.filter(user=user).first()
    now = timezone.now()
    has_access = subscription and subscription.status == 'active' and subscription.end_date > now

    # 💬 Command handling
    if message_body == 'help':
        if has_access:
            resp.message(
                f"Here are your options:"
                f"\n1. Create Order: https://kaziflow.onrender.com/order?phone={phone}"
                f"\n2. View Sales: https://kaziflow.onrender.com/order_list?phone={phone}"
                f"\n3. View Subscription: type *3*"
            )
        else:
            resp.message(
                "❌ Your subscription is inactive or expired.\n"
                f"Renew here: https://kaziflow.onrender.com/start_subscription?phone={phone}"
            )

    elif message_body == '3':
        if has_access:
            end_date = subscription.end_date.strftime('%Y-%m-%d')
            resp.message(f"✅ Your subscription is active until {end_date}.")
        else:
            resp.message(
                "❌ Your subscription is inactive.\n"
                f"Renew here: https://kaziflow.onrender.com/start_subscription?phone={phone}"
            )

    elif message_body in ['hi', 'hello', 'start']:
        resp.message("👋 To get started, type *help* to see your options.")

    else:
        resp.message("🤖 I didn’t understand that. Type *help* to see available commands.")

    return HttpResponse(str(resp), content_type='application/xml')

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

@csrf_exempt 
def delete_order(request):
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        order = get_object_or_404(Order, id=order_id)
        order.delete()
        messages.success(request, f"✅ Order for {order.customer_name} deleted successfully.")
        return redirect(f'/order_list?phone={order.user.phone}')
    return HttpResponse("❌ Invalid request method", status=405)