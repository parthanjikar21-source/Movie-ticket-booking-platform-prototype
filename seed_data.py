from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
from movies.models import Genre, Language, Movie
from theaters.models import City, Theater, Screen, SeatCategory, Seat, Show

class Command(BaseCommand):
    help = "Create development/sample cinema data without credentials."
    def handle(self, *args, **options):
        genres = {name: Genre.objects.get_or_create(name=name, defaults={"slug": slugify(name)})[0] for name in ["Action", "Drama", "Comedy", "Sci-Fi"]}
        languages = {name: Language.objects.get_or_create(name=name)[0] for name in ["English", "Hindi", "Marathi"]}
        movies = []
        samples = [("Midnight Circuit", "A fictional action thriller about a citywide race against time.", 128, "UA", ["Action", "Sci-Fi"]), ("Monsoon Letters", "A fictional drama about friendship, memory and second chances.", 116, "U", ["Drama"]), ("Laughing Weekend", "A fictional comedy about an overbooked family vacation.", 104, "U", ["Comedy"])]
        for title, description, duration, cert, gs in samples:
            movie, _ = Movie.objects.get_or_create(slug=slugify(title), defaults={"title": title, "description": description, "duration_minutes": duration, "certification": cert, "release_date": timezone.now().date(), "is_published": True})
            movie.genres.set([genres[g] for g in gs]); movie.languages.set([languages["English"] if title == "Midnight Circuit" else languages["Hindi"]]); movies.append(movie)
        city, _ = City.objects.get_or_create(slug="pune", defaults={"name": "Pune"})
        theater, _ = Theater.objects.get_or_create(slug="cinebook-pune", defaults={"name": "CineBook Pune", "city": city, "address": "Sample Road, Pune", "active": True})
        screen, _ = Screen.objects.get_or_create(theater=theater, name="Screen 1", defaults={"rows": 8, "columns": 10})
        categories = {n: SeatCategory.objects.get_or_create(name=n)[0] for n in ["Standard", "Premium"]}
        for r in range(1, 9):
            label = chr(64+r)
            for n in range(1, 11):
                Seat.objects.get_or_create(screen=screen, row_label=label, number=n, defaults={"category": categories["Premium"] if r <= 2 else categories["Standard"], "base_price": 300 if r <= 2 else 220})
        for index, movie in enumerate(movies):
            start = timezone.now() + timedelta(days=index + 1, hours=2)
            Show.objects.get_or_create(movie=movie, theater=theater, screen=screen, start_time=start, defaults={"end_time": start + timedelta(minutes=movie.duration_minutes + 20), "price": 220, "active": True})
        self.stdout.write(self.style.SUCCESS("Sample cinema data created."))
