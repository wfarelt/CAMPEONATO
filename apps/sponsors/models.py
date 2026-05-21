from django.db import models


class Sponsor(models.Model):
    name = models.CharField(max_length=120, unique=True, verbose_name="Nombre")
    image = models.ImageField(upload_to="sponsors/", verbose_name="Imagen")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Auspiciador"
        verbose_name_plural = "Auspiciadores"

    def __str__(self):
        return self.name
