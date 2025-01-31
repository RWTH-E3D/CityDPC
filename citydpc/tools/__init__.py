class PartyWallConfig:
    # maximum distance between two surfaces to be considered potentially matching
    GROUNDSURFACE_BUFFER = 0.15
    # maximum angle between two norm vectors of surfaces to be considered
    # potentially matching
    # default is 0.9659  ~= cos(15°)
    MAX_NORM_VECTOR_ANGLE_DIFF = 0.9659

    @classmethod
    def set_groundsurface_buffer(cls, buffer: float):
        if buffer <= 0:
            raise ValueError("Buffer has to be greater than 0")
        cls.GROUNDSURFACE_BUFFER = buffer

    @classmethod
    def set_max_norm_vector_angle_diff(cls, angle: float):
        if angle <= 0:
            raise ValueError("Angle has to be greater than 0")
        cls.MAX_NORM_VECTOR_ANGLE_DIFF = angle
