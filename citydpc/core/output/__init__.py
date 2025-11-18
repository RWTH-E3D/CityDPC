from citydpc.logger import logger


class ExportConfig:
    EXPORT_CITYDPC_IDS = False

    @classmethod
    def set_export_citydpc_ids(cls, value: bool):
        cls.EXPORT_CITYDPC_IDS = value
        logger.info("Setting export_citydpc_ids to: %s", value)
