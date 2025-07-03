from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from ...models import Subscription
from twilio.rest import Client
from decouple import config

class Command(BaseCommand):
    help = 'Send WhatsApp reminders for expiring subscriptions'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        target_date = now + timedelta(days=3)

        expiring_subs = Subscription.objects.filter(end_date__date=target_date.date(), status='active')

        account_sid = config("TWILIO_ACCOUNT_SID")
        auth_token = config("TWILIO_AUTH_TOKEN")
        from_whatsapp = 'whatsapp:+14155238886'
        client = Client(account_sid, auth_token)

        for sub in expiring_subs:
            phone = sub.user.phone
            to_whatsapp = f'whatsapp:+{phone}'
            message = (
                f"🕒 Hello {sub.user.username}, your KaziFlow subscription will expire on {sub.end_date.strftime('%Y-%m-%d')}."
                f"\nPlease renew here: https://681c-196-96-168-243.ngrok-free.app/start_subscription?phone={phone}"
            )
            try:
                client.messages.create(body=message, from_=from_whatsapp, to=to_whatsapp)
                self.stdout.write(self.style.SUCCESS(f"Reminder sent to {phone}"))
            except Exception as e:
                self.stderr.write(f"Error sending to {phone}: {str(e)}")
