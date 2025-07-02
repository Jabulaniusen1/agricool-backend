import os
from datetime import datetime
from typing import Optional

import requests
from common.constants import (
    FIELD_CALLBACK_URL,
    FIELD_PARAMS,
    FRUIT_INDEX,
    JOB_CRATE_ID,
    LAST_TEMPERATURE,
    QUALITY__DT,
    RUN_ID,
    SHELF_LIFE_BUFFER,
    TEMPERATURE_DT,
    TEMPERATURE_HISTORY,
)
from job_queue.settings import (
    ENV_COMSOL_CALLBACK_KEY,
    ENV_FUSE_PATH,
    HEADER_CALLBACK_KEY,
)

from .job_types import ActiveJob



class JobQueueManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(JobQueueManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.fuse_path = ENV_FUSE_PATH
        self.job_queue = []
        self.scheduled_jobs = set()
        self.active_job: Optional[ActiveJob] = None
        self._run_id_counter = 1
        self._initialized = True

    def _get_next_run_id(self) -> int:
        run_id = self._run_id_counter
        self._run_id_counter += 1
        return run_id

    @staticmethod
    def safe_parse_float(s):
        s = s.strip()
        try:
            if "i" in s:
                return abs(complex(s.replace("i", "j")))
            return float(s)
        except ValueError:
            return -1

    def enqueue_job(self, job) -> bool:
        key = job[JOB_CRATE_ID]
        if key in self.scheduled_jobs:
            return False

        job[RUN_ID] = self._get_next_run_id()
        print(f"[QUEUE] Enqueueing job {job[RUN_ID]} [{datetime.now().isoformat()}]")

        self.scheduled_jobs.add(key)
        self.job_queue.append(job)
        return True

    def start_job(self):
        if not self.job_queue:
            return

        job = self.job_queue.pop(0)
        run_id = job[RUN_ID]
        params = job[FIELD_PARAMS]

        print(f"[START] Starting job {run_id} [{datetime.now().isoformat()}]")

        input_params = (
            f"I0_sl\t{params[QUALITY__DT]}\n"
            f"T_fruit_ini\t{params[TEMPERATURE_DT]}\n"
            f"SL_buffer\t{params[SHELF_LIFE_BUFFER]}\n"
            f"FruitIndex\t{params[FRUIT_INDEX]}\n"
            f"T_set\t{round(float(params[LAST_TEMPERATURE]))}\n"
            f"run_ID\t{run_id}\n"
            f"intervall_in_ms\t1000\n"
        )

        print(f"[START] Input params: {input_params}")
        print(f"[START] Temperature Table: {params[TEMPERATURE_HISTORY]}")

        self.active_job = ActiveJob(
            job=job,
            input_params=input_params,
            input_temperature_table=params[TEMPERATURE_HISTORY],
            output_pl="",
            output_values="",
        )

    def end_job(self, success=True):
        if not self.active_job:
            return

        job = self.active_job.job
        print(f"[END] Finishing job {job[RUN_ID]} [{datetime.now().isoformat()}]")

        if not success:
            print("[JOB MANAGER] Job ended with failure.")
            headers = {HEADER_CALLBACK_KEY: ENV_COMSOL_CALLBACK_KEY  }
            requests.post(
                job[FIELD_CALLBACK_URL],
                json={
                    "error": "Job failed",
                    "crate_id": job[JOB_CRATE_ID],

                },
                headers=headers,
            )
            return

        try:
            pl = self.active_job.output_pl.strip()
            val = self.active_job.output_values.strip()

            shelf_life = (
                int(JobQueueManager.safe_parse_float(pl.split()[-1])) if pl else -1
            )

            values = list(filter(None, val.split()))
            quality_dt = (
                JobQueueManager.safe_parse_float(values[1]) if len(values) > 1 else -1
            )
            temperature_dt = (
                JobQueueManager.safe_parse_float(values[2]) if len(values) > 2 else -1
            )

            output_params = {
                "shelf_life": shelf_life,
                "quality_dt": quality_dt,
                "temperature_dt": temperature_dt,
            }

            print(f"[END] Output params: {output_params}")

            headers = {HEADER_CALLBACK_KEY: ENV_COMSOL_CALLBACK_KEY }
            requests.post(
                job[FIELD_CALLBACK_URL],
                json={
                    "crate_id": job[JOB_CRATE_ID],
                    "outputs": output_params,
                },
                headers=headers,
            )

        except Exception as e:
            print(f"[END] Error finishing job {job[RUN_ID]}: {e}")
            headers = {HEADER_CALLBACK_KEY: ENV_COMSOL_CALLBACK_KEY }
            requests.post(
                job[FIELD_CALLBACK_URL],
                json={
                    "error": "Job failed",
                },
                headers=headers,
            )

        finally:
            self.scheduled_jobs.discard(job[JOB_CRATE_ID])
            self.active_job = None
