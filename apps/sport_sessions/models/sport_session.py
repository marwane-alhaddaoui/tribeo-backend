from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from sports.models.sport import Sport
from apps.teams.models.team import Team

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

    # --- Nouveaux champs pour logique Coach ---
    event_type = models.CharField(max_length=16, choices=EventType.choices, default=EventType.TRAINING)
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

    is_public = models.BooleanField(default=True, help_text="⚠️ Hérité de visibility, ne pas modifier manuellement.")
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

    # --- Méthodes utilitaires ---
    def is_full(self):
        return self.participants.count() >= self.max_players

    def available_spots(self):
        return max(self.max_players - self.participants.count(), 0)

    def requires_teams(self):
        return self.team_mode

    def __str__(self):
        return f"{self.title} - {self.sport.name} ({self.date})"
