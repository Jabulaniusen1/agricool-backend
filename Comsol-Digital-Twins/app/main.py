import os
from threading import Thread

from dotenv import load_dotenv

from api import create_app
from fuse import FUSE
from fuse_integration.comsol_fuse import ComsolFuse
from job_queue.queue import JobQueueManager
from job_queue.settings import ENV_FUSE_PATH

load_dotenv()
app = create_app()

if __name__ == "__main__":
    if not os.path.isdir(ENV_FUSE_PATH):
        print(f"[MAIN] Mounting FUSE at {ENV_FUSE_PATH}")
        os.makedirs(ENV_FUSE_PATH, exist_ok=True) # Mounts the FUSE filesystem at the specified path.

    def run_flask():
        print("[MAIN] Starting Flask server...")
        app.run(host="0.0.0.0", port=5900) # TODO: fix

    # Starts the Flask server in a separate thread so it can run concurrently with the FUSE system, mounted below
    Thread(target=run_flask).start()

    # Mounts the FUSE filesystem using the fuse_instance
    fuse_opts = {
        'allow_other': True,
        'default_permissions': True
    }
    FUSE(ComsolFuse(), ENV_FUSE_PATH, foreground=True, **fuse_opts)

        # Initialize the job queue manager
    JobQueueManager()
