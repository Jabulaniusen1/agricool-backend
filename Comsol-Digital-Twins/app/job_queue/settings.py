import os

HEADER_CALLBACK_KEY = "X-Comsol-Callback-Key"

ENV_COMSOL_CALLBACK_KEY = os.getenv("COMSOL_CALLBACK_KEY") or "cH4ng3_m3"
ENV_FUSE_PATH = os.getenv("FUSE_PATH") or "/mnt/comsol"
