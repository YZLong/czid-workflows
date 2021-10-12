import os
import re
from os.path import basename, join
from subprocess import run
import boto3
import requests
import logging
from urllib.parse import urlparse
from multiprocessing import Pool
from botocore.exceptions import ClientError
from .minimap2_scatter import minimap2_merge
from .batch_run_helpers import _run_batch_job, _db_chunks

log = logging.getLogger(__name__)

ALIGNMENT_ALGORITHM = "minimap2"
MAX_CHUNKS_IN_FLIGHT = 5


def get_batch_job_desc_bucket():
    try:
        account_id = boto3.client("sts").get_caller_identity()["Account"]
    except ClientError:
        account_id = requests.get(
            "http://169.254.169.254/latest/dynamic/instance-identity/document"
        ).json()["accountId"]
    return f"aegea-batch-jobs-{account_id}"


class BatchJobFailed(Exception):
    pass


def _run_chunk(
    chunk_id: int, input_dir: str, chunk_dir: str, db_chunk: str, *queries: str
):
    deployment_environment = os.environ["DEPLOYMENT_ENVIRONMENT"]
    priority_name = os.environ.get("PRIORITY_NAME", "normal")
    alignment_algorithm = "minimap2"
    provisioning_model = "EC2"
    pattern = r"s3://.+/samples/([0-9]+)/([0-9]+)/"
    m = re.match(pattern, input_dir)
    if m:
        project_id, sample_id = m.group(1), m.group(2)
    else:
        project_id, sample_id = "0", "0"

    job_name = f"idseq-{deployment_environment}-{alignment_algorithm}-"\
                "project-{project_id}-sample-{sample_id}-part-{chunk_id}"
    job_queue = f"idseq-{deployment_environment}-{alignment_algorithm}-{provisioning_model}-{priority_name}"
    job_definition = f"idseq-{deployment_environment}-{alignment_algorithm}"

    environment = [
        {
            "name": "DB_CHUNK",
            "value": db_chunk,
        },
        {
            "name": "OUTPUT_DIR",
            "value": chunk_dir,
        },
    ]

    for i, query in enumerate(queries):
        environment.append(
            {
                "name": f"QUERY_{i}",
                "value": join(input_dir, basename(query)),
            }
        )

    _run_batch_job(
        job_name=job_name,
        job_queue=job_queue,
        job_definition=job_definition,
        environment=environment,
        chunk_id=chunk_id,
        retries=2,
    )


def run_minimap2(
    input_dir: str, chunk_dir: str, db_path: str, result_path: str, *queries: str
):
    parsed_url = urlparse(db_path, allow_fragments=False)
    bucket = parsed_url.netloc
    prefix = parsed_url.path.lstrip("/")
    chunks = (
        [chunk_id, input_dir, chunk_dir, f"s3://{bucket}/{db_chunk}", *queries]
        for chunk_id, db_chunk in enumerate(_db_chunks(bucket, prefix))
    )
    with Pool(MAX_CHUNKS_IN_FLIGHT) as p:
        p.starmap(_run_chunk, chunks)
    run(["s3parcp", "--recursive", chunk_dir, "chunks"], check=True)
    minimap2_merge("chunks", result_path, *queries)
