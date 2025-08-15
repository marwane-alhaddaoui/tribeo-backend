from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from sports.models.sport import Sport  # garde comme chez toi si c'est bien ce chemin
from apps.teams.models.team import Team
from django.utils import timezone
from datetime import datetime

class SportSession(models.Model):
    """
    Représente une session sportive créée par un utilisateur ou un coach.
    """

    # --- Nouveaux ENUMS ---
    class EventType(models.TextChoices):
        TRAINING = "TRAINING", "Entraînement"
        FRIENDLY = "FRIENDLY", "Match amical"
        COMPETITION = "COMPETITION", "Compétition"

    class Format(models.TextChoices):
        SOLO = "SOLO", "Solo"
        TEAM = "TEAM", "Équipe unique"
        VERSUS_1V1 = "VERSUS_1V1", "1 contre 1"
        VERSUS_TEAM = "VERSUS_TEAM", "Équipe contre équipe"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Brouillon"
        OPEN = "OPEN", "Ouvert"
        LOCKED = "LOCKED", "Verrouillé"
        FINISHED = "FINISHED", "Terminé"
        CANCELED = "CANCELED", "Annulé"

    # 🔥 Nouveau : visibilité
    class Visibility(models.TextChoices):
        PRIVATE = "PRIVATE", "Privée (coach uniquement)"
        GROUP = "GROUP", "Groupe (membres du groupe)"
        PUBLIC = "PUBLIC", "Publique (tout le monde)"

    # Informations générales
    title = models.CharField(max_length=100, help_text="Nom ou titre de la session.")
    sport = models.ForeignKey(Sport, on_delete=models.PROTECT, related_name="sessions")
    description = models.TextField(blank=True, null=True, help_text="Détails ou règles de la session.")
    location = models.CharField(max_length=255, help_text="Lieu où se déroulera la session (adresse complète ou ville).")
    latitude = models.FloatField(blank=True, null=True, help_text="Latitude de l'emplacement.")
    longitude = models.FloatField(blank=True, null=True, help_text="Longitude de l'emplacement.")
    date = models.DateField(help_text="Date de la session.")
    start_time = models.TimeField(help_text="Heure de début de la session.")

    # --- Champs coach / logique session ---
    event_type = models.CharField(max_length=16, choices=EventType.choices, default=EventType.FRIENDLY)
    format = models.CharField(max_length=16, choices=Format.choices, default=Format.SOLO)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    requires_approval = models.BooleanField(default=False, help_text="Si activé, le coach doit approuver les demandes.")

    # Versus (optionnels)
    home_team = models.ForeignKey("teams.Team", null=True, blank=True, on_delete=models.SET_NULL, related_name="home_sessions")
    away_team = models.ForeignKey("teams.Team", null=True, blank=True, on_delete=models.SET_NULL, related_name="away_sessions")
    score_home = models.IntegerField(null=True, blank=True)
    score_away = models.IntegerField(null=True, blank=True)

    # Paramètres d'inscription
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PRIVATE)
    group = models.ForeignKey("groups.Group", null=True, blank=True, on_delete=models.SET_NULL, related_name="sessions")

    # ✅ cohérent avec visibility par défaut (PRIVATE)
    is_public = models.BooleanField(default=False, help_text="⚠️ Hérité de visibility, ne pas modifier manuellement.")
    team_mode = models.BooleanField(default=False, help_text="Active les équipes pour les sports à adversité.")
    max_players = models.PositiveIntegerField(default=10, validators=[MinValueValidator(1)], help_text="Nombre total max.")
    min_players_per_team = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1)], help_text="Min par équipe.")
    max_players_per_team = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1)], help_text="Max par équipe.")

    # Relations utilisateurs
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_sessions', help_text="Créateur")
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='joined_sessions', blank=True, help_text="Participants")

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sport_session'
        ordering = ['date', 'start_time']
        verbose_name = "Session sportive"
        verbose_name_plural = "Sessions sportives"

    def save(self, *args, **kwargs):
        """Synchronise is_public avec visibility"""
        self.is_public = (self.visibility == self.Visibility.PUBLIC)
        super().save(*args, **kwargs)

    # --- Méthodes utilitaires / capacité ---
    def attendees_count(self) -> int:
        internals = self.participants.count()
        externals = self.external_attendees.count()
        return internals + externals

    def is_full(self) -> bool:
        return bool(self.max_players) and self.attendees_count() >= self.max_players

    def available_spots(self) -> int:
        if not self.max_players:
            return 999999
        return max(self.max_players - self.attendees_count(), 0)

    # ---- time helpers ----
    def start_datetime(self):
        dt = datetime.combine(self.date, self.start_time)
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    def has_started(self) -> bool:
        return timezone.now() >= self.start_datetime()

    def required_players(self) -> int:
        # Seuil mini pour considérer une session "valide"
        if self.team_mode and self.min_players_per_team:
            return max(2, self.min_players_per_team * 2)
        # défaut: 2 (ou 1 si max_players=1)
        if self.max_players and self.max_players < 2:
            return self.max_players
        return 2

    def compute_status(self) -> str:
        # Passé → FINISHED/CANCELED selon seuil mini atteint
        if self.has_started():
            return (self.Status.FINISHED
                    if self.attendees_count() >= self.required_players()
                    else self.Status.CANCELED)
        # Futur → lock si complet
        if self.is_full():
            return self.Status.LOCKED
        # Sinon ouvert
        return self.Status.OPEN

    def apply_status(self, persist: bool = True) -> str:
        new_status = self.compute_status()
        if new_status != self.status:
            self.status = new_status
            if persist:
                self.save(update_fields=["status"])
        return self.status

    def __str__(self):
        return f"{self.title} - {self.sport.name} ({self.date})"
