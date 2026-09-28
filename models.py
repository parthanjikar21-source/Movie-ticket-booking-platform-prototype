from django.db import models
from django.core.validators import MinValueValidator
from movies.models import Movie

class City(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True)
    def __str__(self): return self.name

class Theater(models.Model):
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="theaters")
    address = models.TextField()
    active = models.BooleanField(default=True, db_index=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["city", "name"], name="unique_theater_city_name")]
        indexes = [models.Index(fields=["city", "active"])]
    def __str__(self): return f"{self.name}, {self.city.name}"

class Screen(models.Model):
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, related_name="screens")
    name = models.CharField(max_length=80)
    rows = models.PositiveIntegerField(default=8)
    columns = models.PositiveIntegerField(default=12)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["theater", "name"], name="unique_screen_theater_name")]
    def __str__(self): return f"{self.theater.name} - {self.name}"

class SeatCategory(models.Model):
    name = models.CharField(max_length=60, unique=True)
    description = models.CharField(max_length=200, blank=True)
    def __str__(self): return self.name

class Seat(models.Model):
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, related_name="seats")
    row_label = models.CharField(max_length=5)
    number = models.PositiveIntegerField()
    category = models.ForeignKey(SeatCategory, on_delete=models.PROTECT, related_name="seats")
    base_price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    class Meta:
        constraints = [models.UniqueConstraint(fields=["screen", "row_label", "number"], name="unique_seat_position")]
        ordering = ["row_label", "number"]
        indexes = [models.Index(fields=["screen", "row_label", "number"])]
    @property
    def label(self): return f"{self.row_label}{self.number}"
    def __str__(self): return f"{self.screen} {self.label}"

class Show(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.PROTECT, related_name="shows")
    theater = models.ForeignKey(Theater, on_delete=models.PROTECT, related_name="shows")
    screen = models.ForeignKey(Screen, on_delete=models.PROTECT, related_name="shows")
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField()
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [models.Index(fields=["movie", "start_time"]), models.Index(fields=["theater", "start_time"]), models.Index(fields=["screen", "start_time"])]
        constraints = [models.CheckConstraint(condition=models.Q(end_time__gt=models.F("start_time")), name="show_end_after_start")]
    def __str__(self): return f"{self.movie.title} - {self.theater.name} - {self.start_time:%d %b %Y %H:%M}"
