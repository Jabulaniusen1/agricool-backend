import errno
from datetime import datetime
from pathlib import Path

from common.constants import RUN_ID
from fuse import FuseOSError, Operations
from fuse_integration.constants import (
    FILENAME_CONTROL_ROOT,
    FILENAME_CRASH_LOGS,
    FILENAME_ERROR,
    FILENAME_EVENT_LOOP,
    FILENAME_INPUT_T,
    FILENAME_OUTPUT_PL_PREFIX,
    FILENAME_OUTPUT_VALUES_PREFIX,
    PERMISSIONS_DIRECTORY,
    PERMISSIONS_FILE,
)
from job_queue.queue import JobQueueManager

from .timed_lru_cache import timed_lru_cache


class ComsolFuse(Operations):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ComsolFuse, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        self.directories = set(["/"])
        self.files = set()
        self.job_write_data = {}
        self.job_queue_manager = JobQueueManager()
        self.last_event_loop_access_time = None

        self.path_control = f"/{FILENAME_CONTROL_ROOT}"
        self.path_input_t = f"/{FILENAME_INPUT_T}"
        self.path_event_loop = f"/{FILENAME_EVENT_LOOP}"

    @staticmethod
    def extract_run_id(filename: str):
        try:
            return filename.split("ID")[1].split(".")[0]
        except IndexError:
            return None

    def cleanup_job_output_files(self, run_id):
        for prefix in [FILENAME_OUTPUT_PL_PREFIX, FILENAME_OUTPUT_VALUES_PREFIX]:
            job_file = f"/{prefix}{run_id}.txt"
            self.job_write_data.pop(job_file, None)
            self.files.discard(job_file)

    @property
    def active_job_obj(self):
        return self.job_queue_manager.active_job

    @property
    def active_job(self):
        return self.active_job_obj.job if self.active_job_obj else None

    def readdir(self, path, fh):
        yield "."
        yield ".."
        if path == "/":
            yield FILENAME_EVENT_LOOP
            yield FILENAME_INPUT_T
            yield FILENAME_CONTROL_ROOT

    def getattr(self, path, fh=None):
        if path in self.directories:
            return {"st_mode": PERMISSIONS_DIRECTORY, "st_nlink": 2}

        if path in (self.path_control, self.path_event_loop, self.path_input_t):
            try:
                content = self.read_file_content(path)
                return {
                    "st_mode": PERMISSIONS_FILE,
                    "st_nlink": 1,
                    "st_size": len(content),
                }
            except FuseOSError:
                raise FuseOSError(errno.ENOENT)

        if path in self.job_write_data:
            size = len(self.job_write_data[path])
            return {"st_mode": PERMISSIONS_FILE, "st_nlink": 1, "st_size": size}

        if path.startswith(f"/{FILENAME_OUTPUT_PL_PREFIX}") or path.startswith(
            f"/{FILENAME_OUTPUT_VALUES_PREFIX}"
        ):
            return {"st_mode": PERMISSIONS_FILE, "st_nlink": 1, "st_size": 0}

        raise FuseOSError(errno.ENOENT)

    def mkdir(self, path, mode):
        self.directories.add(path)
        return 0

    def create(self, path, mode, fi=None):
        self.files.add(path)
        self.job_write_data[path] = b""
        return 0

    def rename(self, old, new):
        if old in self.job_write_data:
            self.job_write_data[new] = self.job_write_data.pop(old)
            self.files.discard(old)
            self.files.add(new)
            return 0
        raise FuseOSError(errno.ENOENT)

    def read(self, path, size, offset, fh):
        try:
            content = self.read_file_content(path)

            if content is None:
                raise FuseOSError(errno.ENOENT)

            if isinstance(content, str):
                content = content.encode()
            return content[offset : offset + size]

        except FuseOSError as e:
            raise e
        except Exception as e:
            print(f"[ERROR] Failed to read {path}: {e}")
            raise FuseOSError(errno.EIO)

    def write(self, path, data, offset, fh):
        filename = Path(path).name

        if FILENAME_ERROR in filename:
            crash_path = f"{FILENAME_CRASH_LOGS}{filename}"
            if crash_path not in self.job_write_data:
                self.job_write_data[crash_path] = bytearray()
            content = self.job_write_data[crash_path]
            content[offset : offset + len(data)] = data

            if self.active_job:
                self.job_queue_manager.end_job(False)
            return len(data)

        if not self.active_job:
            raise FuseOSError(errno.EIO)

        run_id = self.active_job[RUN_ID]
        print(f"[WRITE] job {run_id} [{datetime.now().isoformat()}]")

        self.files.add(path)
        if path not in self.job_write_data:
            self.job_write_data[path] = bytearray()

        content = self.job_write_data[path]
        if len(content) < offset:
            content.extend(b"\x00" * (offset - len(content)))
        content[offset : offset + len(data)] = data

        if FILENAME_OUTPUT_PL_PREFIX in filename:
            extracted_run_id = self.extract_run_id(filename)
            if str(run_id) == str(extracted_run_id):
                self.active_job_obj.output_pl = self.job_write_data[path].decode(
                    errors="ignore"
                )

        elif FILENAME_OUTPUT_VALUES_PREFIX in filename:
            extracted_run_id = self.extract_run_id(filename)
            if str(run_id) == str(extracted_run_id):
                self.active_job_obj.output_values = self.job_write_data[path].decode(
                    errors="ignore"
                )

        if self.active_job_obj.output_pl and self.active_job_obj.output_values:
            self.job_queue_manager.end_job()
            self.cleanup_job_output_files(run_id)

        return len(data)

    def open(self, path, flags):
        return 0

    def truncate(self, path, length, fh=None):
        if path in self.job_write_data:
            self.job_write_data[path] = self.job_write_data[path][:length]
        return 0

    def flush(self, path, fh):
        return 0

    def fsync(self, path, datasync, fh):
        return 0

    @timed_lru_cache()
    def read_file_content(self, path):
        content = None

        if path == self.path_control:
            content = ""

        elif path == self.path_input_t:
            content = self.generate_input_temperatures_file()

        elif path == self.path_event_loop:
            self.last_event_loop_access_time = datetime.now()
            content = self.generate_event_loop_control()

        if content is None:
            raise FuseOSError(errno.ENOENT)

        return content

    def generate_input_temperatures_file(self):
        if not self.active_job_obj:
            raise FuseOSError(errno.ENOENT)

        print(f"[INPUT_T] job {self.active_job[RUN_ID]} [{datetime.now().isoformat()}]")
        return self.active_job_obj.input_temperature_table.encode()

    def generate_event_loop_control(self):
        if not self.active_job:
            self.job_queue_manager.start_job()

        if self.active_job:
            run_id = self.active_job[RUN_ID]
            print(f"[EVENT LOOP] job {run_id} [{datetime.now().isoformat()}]")
            self.job_write_data[FILENAME_EVENT_LOOP] = (
                self.active_job_obj.input_params.encode()
            )
            return self.active_job_obj.input_params.encode()

        return (
            "I0_sl\t0\n"
            "T_fruit_ini\t0\n"
            "SL_buffer\t0\n"
            "FruitIndex\t0\n"
            "T_set\t0\n"
            "run_ID\t0\n"
        ).encode()
