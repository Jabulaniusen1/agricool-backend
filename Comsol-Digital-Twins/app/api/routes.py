from datetime import datetime, timedelta
from http import HTTPStatus

from api.constants.api_routes import ROUTE_HEALTH, ROUTE_SCHEDULE, ROUTE_STATUS
from api.constants.http import (
    HTTP_GET,
    MSG_ALREADY_SCHEDULED,
    MSG_ERROR_MISSING_CONTEXT,
    MSG_ERROR_MISSING_FIELDS,
    MSG_EVENTLOOP_OK,
    MSG_EVENTLOOP_OLD,
    MSG_JOB_QUEUED,
)
from common.constants import (
    FIELD_CALLBACK_URL,
    FIELD_CONTEXT,
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
from flask import Blueprint, jsonify, request
from job_queue.queue import JobQueueManager
from fuse_integration.comsol_fuse import ComsolFuse

api = Blueprint("api", __name__)

CONTEXT_FIELDS_REQUIRED = {JOB_CRATE_ID}
PARAM_FIELDS_REQUIRED = {
    FRUIT_INDEX,
    QUALITY__DT,
    SHELF_LIFE_BUFFER,
    TEMPERATURE_DT,
    LAST_TEMPERATURE,
    TEMPERATURE_HISTORY,
}
REQUIRED_TOP_FIELDS = {FIELD_CONTEXT, FIELD_PARAMS, FIELD_CALLBACK_URL}
HEALTH_TIMEOUT_MINUTES = 5

job_queue_manager = JobQueueManager()
comsol_fuse = ComsolFuse()

def format_job_data(job):
    return {
        RUN_ID: job.get(RUN_ID),
        JOB_CRATE_ID: job.get(JOB_CRATE_ID),
        FIELD_PARAMS: job.get(FIELD_PARAMS),
    }


@api.route(ROUTE_SCHEDULE, methods=["POST"])
def submit_job():
    data = request.get_json()

    if not data or not REQUIRED_TOP_FIELDS.issubset(data):
        return jsonify({"error": MSG_ERROR_MISSING_FIELDS}), HTTPStatus.BAD_REQUEST

    context = data[FIELD_CONTEXT]
    params = data[FIELD_PARAMS]

    if not CONTEXT_FIELDS_REQUIRED.issubset(
        context
    ) or not PARAM_FIELDS_REQUIRED.issubset(params):
        return jsonify({"error": MSG_ERROR_MISSING_CONTEXT}), HTTPStatus.BAD_REQUEST

    job = {
        JOB_CRATE_ID: context[JOB_CRATE_ID],
        FIELD_PARAMS: {key: params[key] for key in PARAM_FIELDS_REQUIRED},
        FIELD_CALLBACK_URL: data[FIELD_CALLBACK_URL],
    }

    if not job_queue_manager.enqueue_job(job):
        return jsonify({"message": MSG_ALREADY_SCHEDULED}), HTTPStatus.OK

    return (
        jsonify(
            {
                "message": MSG_JOB_QUEUED,
                "jobCrateId": context[JOB_CRATE_ID],
            }
        ),
        HTTPStatus.CREATED,
    )


@api.route(ROUTE_STATUS, methods=["GET"])
def status_check():
    active_job_data = (
        format_job_data(job_queue_manager.active_job.job)
        if job_queue_manager.active_job
        else None
    )

    pending_jobs_data = [format_job_data(job) for job in job_queue_manager.job_queue]
    last_event_loop_access_time = comsol_fuse.last_event_loop_access_time

    return (
        jsonify(
            {
                "activeJob": active_job_data,
                "queuedJobs": pending_jobs_data,
                "lastEventLoopAccess": (
                    last_event_loop_access_time.isoformat()
                    if last_event_loop_access_time
                    else None
                ),
            }
        ),
        HTTPStatus.OK,
    )


@api.route(ROUTE_HEALTH, methods=[HTTP_GET])
def health_check():
    now = datetime.now()
    max_age = timedelta(minutes=HEALTH_TIMEOUT_MINUTES)
    last_event_loop_access_time = comsol_fuse.last_event_loop_access_time


    if last_event_loop_access_time and now - last_event_loop_access_time < max_age:
        return (
            jsonify(
                {
                    "status": HTTPStatus.OK.phrase,
                    "message": MSG_EVENTLOOP_OK,
                }
            ),
            HTTPStatus.OK,
        )
    else:
        return (
            jsonify(
                {
                    "status": HTTPStatus.SERVICE_UNAVAILABLE.phrase,
                    "message": MSG_EVENTLOOP_OLD,
                }
            ),
            HTTPStatus.SERVICE_UNAVAILABLE,
        )
