from celery import shared_task
from django.core.mail import EmailMessage
from django.utils import timezone
from bookings.models import Booking
from .services import generate_ticket, ticket_pdf_bytes

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def generate_and_email_ticket(self, booking_id):
    booking = Booking.objects.select_related("user", "show__movie", "show__theater", "show__screen", "payment").prefetch_related("booking_seats__show_seat__seat").get(pk=booking_id)
    if booking.status != Booking.Status.CONFIRMED: return
    ticket = generate_ticket(booking)
    data = ticket_pdf_bytes(ticket)
    if not data: return
    email = EmailMessage(subject=f"Your cinema ticket - {booking.reference}", body=f"Your booking for {booking.show.movie.title} is confirmed. Booking ID: {booking.reference}.", to=[booking.user.email])
    email.attach(f"{booking.reference}.pdf", data, "application/pdf")
    email.send(fail_silently=False)
    ticket.emailed_at = timezone.now(); ticket.save(update_fields=["emailed_at"])
