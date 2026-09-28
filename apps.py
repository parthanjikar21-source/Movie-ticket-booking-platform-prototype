from django.apps import AppConfig
class TheatersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "theaters"
    def ready(self):
        from django.db.models.signals import post_save
        from .models import Show
        def create_show_seats(sender, instance, created, **kwargs):
            if created:
                from bookings.models import ShowSeat
                ShowSeat.objects.bulk_create([ShowSeat(show=instance, seat=seat) for seat in instance.screen.seats.all()], ignore_conflicts=True, batch_size=500)
        post_save.connect(create_show_seats, sender=Show, dispatch_uid="create_show_seats")
