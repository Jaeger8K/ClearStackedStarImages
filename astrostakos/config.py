class Config:
    """Configuration parameters for star enhancement"""
    BG_KERNEL = 75
    THRESH_SIGMA = 3.0
    STRETCH_STRENGTH = 10.0
    NUM_WORKERS = 8
    BLOCK_SIZE = 512
    OVERLAP = 150
    ENHANCE_FACTOR = 1.3
    DIM_STAR_BOOST = 3.5
    BRIGHT_STAR_THRESHOLD = 0.3
    GAMMA = 2.2
    USE_CIRCULAR_KERNEL = True
