def assign_number(instance, prefix, field="number"):
    """Friendly sequential reference (e.g. CHG-000042) derived from the primary key after insert."""
    if not getattr(instance, field):
        setattr(instance, field, f"{prefix}-{instance.pk:06d}")
        type(instance).objects.filter(pk=instance.pk).update(**{field: getattr(instance, field)})
    return instance
