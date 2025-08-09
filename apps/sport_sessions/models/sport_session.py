from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from sports.models.sport import Sport

class SportSession(models.Model):
    """
    Représente une session sportive créée par un utilisateur ou un coach.
    Peut être ouverte à tous ou privée, avec ou sans adversité (team_mode).
    Sert de base à la recherche de coéquipiers, à l'organisation de matchs
    et à l'intégration future dans des tournois.
    """

    # Informations générales
    title = models.CharField(
        max_length=100,
        help_text="Nom ou titre de la session."
    )

    sport = models.ForeignKey(
        Sport,
        on_delete=models.PROTECT,
        related_name="sessions"
    )

    description = models.TextField(
        blank=True,
        null=True,
        help_text="Détails ou règles de la session."
    )

    location = models.CharField(
        max_length=255,
        help_text="Lieu où se déroulera la session."
    )
    date = models.DateField(help_text="Date de la session.")
    start_time = models.TimeField(help_text="Heure de début de la session.")

    # Paramètres d'inscription
    is_public = models.BooleanField(
        default=True,
        help_text="Session ouverte à tous les utilisateurs."
    )
    team_mode = models.BooleanField(
        default=False,
        help_text="Active les équipes pour les sports à adversité."
    )
    max_players = models.PositiveIntegerField(
        default=10,
        validators=[MinValueValidator(1)],
        help_text="Nombre total maximum de participants."
    )
    min_players_per_team = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Minimum de joueurs par équipe (optionnel, si team_mode)."
    )
    max_players_per_team = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Maximum de joueurs par équipe (optionnel, si team_mode)."
    )

    # Relations avec les utilisateurs
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_sessions',
        help_text="Utilisateur ayant créé la session."
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='joined_sessions',
        blank=True,
        help_text="Utilisateurs inscrits à la session."
    )

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sport_session'
        ordering = ['date', 'start_time']
        verbose_name = "Session sportive"
        verbose_name_plural = "Sessions sportives"

    def is_full(self):
        """Vérifie si la session a atteint son nombre maximum de participants."""
        return self.participants.count() >= self.max_players

    def available_spots(self):
        """Retourne le nombre de places restantes dans la session."""
        return max(self.max_players - self.participants.count(), 0)

    def requires_teams(self):
        """Indique si la session nécessite des équipes distinctes."""
        return self.team_mode

    def __str__(self):
        return f"{self.title} - {self.sport.name} ({self.date})"
