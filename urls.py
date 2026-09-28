from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from movies.views import home

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("accounts/", include("accounts.urls")),
    path("movies/", include("movies.urls")),
    path("theaters/", include("theaters.urls")),
    path("bookings/", include("bookings.urls")),
    path("payments/", include("payments.urls")),
    path("tickets/", include("tickets.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("favicon.ico", RedirectView.as_view(url=settings.STATIC_URL + "img/favicon.svg", permanent=False)),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
