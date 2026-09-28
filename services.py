import razorpay
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from bookings.models import Booking, BookingSeat, ShowSeat
from .models import Payment

def razorpay_client():
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise RuntimeError("Razorpay credentials are not configured")
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def create_razorpay_order(booking):
    client = razorpay_client()
    amount_paise = int(booking.total_amount * 100)
    order = client.order.create({"amount": amount_paise, "currency": settings.RAZORPAY_CURRENCY, "receipt": booking.reference, "notes": {"booking_reference": booking.reference}})
    payment, _ = Payment.objects.update_or_create(booking=booking, defaults={"order_id": order["id"], "amount": booking.total_amount, "currency": settings.RAZORPAY_CURRENCY, "status": Payment.Status.CREATED})
    return payment

def confirm_booking_from_payment(payment_id, order_id, signature):
    client = razorpay_client()
    client.utility.verify_payment_signature({"razorpay_order_id": order_id, "razorpay_payment_id": payment_id, "razorpay_signature": signature})
    with transaction.atomic():
        payment = Payment.objects.select_for_update().select_related("booking").get(order_id=order_id)
        if payment.payment_id == payment_id and payment.status == Payment.Status.CAPTURED:
            return payment.booking
        booking = Booking.objects.select_for_update().get(pk=payment.booking_id)
        if booking.status == Booking.Status.CONFIRMED:
            payment.payment_id = payment_id; payment.signature = signature; payment.status = Payment.Status.CAPTURED; payment.save(update_fields=["payment_id", "signature", "status", "updated_at"])
            return booking
        seats = list(ShowSeat.objects.select_for_update().filter(booking_seats__booking=booking).distinct())
        now = timezone.now()
        if booking.status != Booking.Status.PENDING or len(seats) != booking.quantity or any(s.status != ShowSeat.Status.HELD or s.hold_token != booking.hold_token or not s.hold_expires_at or s.hold_expires_at <= now for s in seats):
            booking.status = Booking.Status.FAILED; booking.save(update_fields=["status", "updated_at"])
            raise ValueError("The seat hold has expired or is no longer valid.")
        for seat in seats:
            seat.status = ShowSeat.Status.BOOKED; seat.held_by = None; seat.hold_token = None; seat.hold_expires_at = None; seat.save(update_fields=["status", "held_by", "hold_token", "hold_expires_at"])
        booking.status = Booking.Status.CONFIRMED; booking.confirmed_at = now; booking.save(update_fields=["status", "confirmed_at", "updated_at"])
        payment.payment_id = payment_id; payment.signature = signature; payment.status = Payment.Status.CAPTURED; payment.save(update_fields=["payment_id", "signature", "status", "updated_at"])
        return booking

def mark_payment_failed(order_id, payload=None):
    with transaction.atomic():
        payment = Payment.objects.select_for_update().select_related("booking").filter(order_id=order_id).first()
        if not payment or payment.status == Payment.Status.CAPTURED: return
        payment.status = Payment.Status.FAILED; payment.raw_payload = payload or {}; payment.save(update_fields=["status", "raw_payload", "updated_at"])
        booking = Booking.objects.select_for_update().get(pk=payment.booking_id)
        if booking.status == Booking.Status.PENDING:
            booking.status = Booking.Status.FAILED; booking.save(update_fields=["status", "updated_at"])
            seats = ShowSeat.objects.select_for_update().filter(booking_seats__booking=booking).distinct()
            for seat in seats:
                seat.status = ShowSeat.Status.AVAILABLE; seat.held_by = None; seat.hold_token = None; seat.hold_expires_at = None; seat.save(update_fields=["status", "held_by", "hold_token", "hold_expires_at"])

def capture_payment_from_webhook(payment_id, order_id, payload):
    with transaction.atomic():
        payment = Payment.objects.select_for_update().select_related("booking").get(order_id=order_id)
        if payment.payment_id == payment_id and payment.status == Payment.Status.CAPTURED:
            return payment.booking
        booking = Booking.objects.select_for_update().get(pk=payment.booking_id)
        if booking.status == Booking.Status.CONFIRMED:
            payment.payment_id = payment_id; payment.status = Payment.Status.CAPTURED; payment.raw_payload = payload; payment.save(update_fields=["payment_id", "status", "raw_payload", "updated_at"]); return booking
        seats = list(ShowSeat.objects.select_for_update().filter(booking_seats__booking=booking).distinct())
        now = timezone.now()
        if booking.status != Booking.Status.PENDING or len(seats) != booking.quantity or any(s.status != ShowSeat.Status.HELD or s.hold_token != booking.hold_token or not s.hold_expires_at or s.hold_expires_at <= now for s in seats):
            booking.status = Booking.Status.FAILED; booking.save(update_fields=["status", "updated_at"]); raise ValueError("The seat hold has expired or is no longer valid.")
        for seat in seats:
            seat.status = ShowSeat.Status.BOOKED; seat.held_by = None; seat.hold_token = None; seat.hold_expires_at = None; seat.save(update_fields=["status", "held_by", "hold_token", "hold_expires_at"])
        booking.status = Booking.Status.CONFIRMED; booking.confirmed_at = now; booking.save(update_fields=["status", "confirmed_at", "updated_at"])
        payment.payment_id = payment_id; payment.status = Payment.Status.CAPTURED; payment.raw_payload = payload; payment.save(update_fields=["payment_id", "status", "raw_payload", "updated_at"])
        return booking
