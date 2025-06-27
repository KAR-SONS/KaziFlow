from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils.http import urlencode
from twilio.twiml.messaging_response import MessagingResponse
from .models import User, Order
from .forms import UserForm, OrderForm
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from django.db.models import Sum


def home(request):
    # Example of querying the User model
    all_users = User.objects.all()
    return render(request, 'home.html', {'all': all_users})

def join(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save()

            # After saving user, redirect to WhatsApp with a custom message
            message = f"Thanks for signing up {user.username}! You can now place orders by texting me here."
            encoded_message = urlencode({'text': message})
            whatsapp_number = '14155238886'  # Replace with your Twilio sandbox number (no "+")

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
            return redirect('order_list')  # or your own confirmation page
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

def subscription(request):
    # This function would handle subscription-related logic
    # For now, we can just render a placeholder template
    return render(request, 'subscription.html')

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
                f"Please sign up here: https://568c-196-96-116-22.ngrok-free.app/join?phone={phone}"
            )
        else:
            if message_body == 'help':
                resp.message(
                    f"Here are your options:"
                    f"\n1. Create Order: https://568c-196-96-116-22.ngrok-free.app/order?phone={phone}"
                    f"\n2. View Sales: https://568c-196-96-116-22.ngrok-free.app/order_list?phone={phone}"
                    f"\n3. Pay for Subscription"
                )
            else:
                resp.message("👋 Welcome back! Type 'help' for options.")

        return HttpResponse(str(resp), content_type='application/xml')

    return HttpResponse("Invalid request", status=400)