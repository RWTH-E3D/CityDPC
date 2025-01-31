class SurfaceConfig:
    DISTANCE_BETWEEN_LINE_AND_POINT = 0.01

    @classmethod
    def set_distance_between_line_and_point(cls, distance: float):
        if distance <= 0:
            raise ValueError("Distance has to be greater than 0")
        cls.DISTANCE_BETWEEN_LINE_AND_POINT = distance
