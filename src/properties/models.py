from collections.abc import Iterable

from django.db import models

from common.text import normalize


class TransactionType(models.TextChoices):
    RENT = "aluguel", "Aluguel"
    SALE = "venda", "Venda"


class Property(models.Model):
    code = models.CharField(max_length=32, unique=True)
    transaction_type = models.CharField(max_length=16, choices=TransactionType.choices)
    neighborhood = models.CharField(max_length=120)
    neighborhood_key = models.CharField(max_length=120, db_index=True, editable=False)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    bedrooms = models.PositiveSmallIntegerField()
    address = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    source = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "properties"
        ordering = ("price", "code")
        indexes = [
            models.Index(fields=["transaction_type", "neighborhood_key", "price"]),
        ]

    def __str__(self) -> str:
        return f"{self.code} ({self.neighborhood}, {self.transaction_type})"

    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        self.neighborhood_key = normalize(self.neighborhood)
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )
