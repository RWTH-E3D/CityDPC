from citydpc.logger import logger
CALC_ROOF_VOLUME_ON_IMPORT = False
CHECK_IF_SURFACES_ARE_PLANAR = True
FIX_GROUNDSURFACE_OUTLIERS = False


def set_roof_volume_calculation(value: bool) -> None:
    global CALC_ROOF_VOLUME_ON_IMPORT
    logger.info("Setting roof volume calculation to: %s", value)
    CALC_ROOF_VOLUME_ON_IMPORT = value


def set_check_if_surfaces_are_planar(value: bool) -> None:
    global CHECK_IF_SURFACES_ARE_PLANAR
    logger.info("Setting check if surfaces are planar to: %s", value)
    CHECK_IF_SURFACES_ARE_PLANAR = value


def set_fix_groundsurface_outliers(value: bool) -> None:
    global FIX_GROUNDSURFACE_OUTLIERS
    logger.info("Setting fix ground surface outliers to: %s", value)
    FIX_GROUNDSURFACE_OUTLIERS = value
