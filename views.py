from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from .models import City, Theater, Show

def theater_list(request):
    city_slug = request.GET.get("city")
    theaters = Theater.objects.filter(active=True).select_related("city").prefetch_related("screens")
    if city_slug: theaters = theaters.filter(city__slug=city_slug)
    return render(request, "theaters/theater_list.html", {"theaters": theaters, "cities": City.objects.all()})

def theater_detail(request, slug):
    theater = get_object_or_404(Theater.objects.select_related("city").prefetch_related("screens"), slug=slug, active=True)
    shows = Show.objects.filter(theater=theater, active=True, start_time__gte=timezone.now()).select_related("movie", "screen").order_by("start_time")
    return render(request, "theaters/theater_detail.html", {"theater": theater, "shows": shows})
