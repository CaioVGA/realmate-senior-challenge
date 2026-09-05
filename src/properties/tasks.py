import logging

from celery import shared_task

from properties.services import import_properties

logger = logging.getLogger(__name__)


@shared_task(name="properties.tasks.import_properties_task")
def import_properties_task() -> dict[str, int]:
    summary = import_properties()
    logger.info("Carga diária concluída: %s", summary)
    return {"created": summary.created, "updated": summary.updated, "skipped": summary.skipped}
