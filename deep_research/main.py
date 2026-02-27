from dotenv import load_dotenv
from openai import OpenAI
import re
import os
import json
import sqlite3
import time
from datetime import datetime, timedelta
from collections import deque
from prompt_gen import prompt_gen

load_dotenv("../.env")  # Load environment variables from .env file
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_PATH = "ccas_city.db"
MAX_BATCH_SIZE = 500
JOB_TIMEOUT_MINUTES = 20
POLL_INTERVAL = 1  # seconds
MAX_RETRIES = 2

class Job:
    def __init__(self, rowid, country, city, education_level):
        self.rowid = rowid
        self.country = country
        self.city = city
        self.education_level = education_level
        self.job_id = None
        self.submitted_at = None
        self.completed = False  # job finished successfully
        self.failed = False     # job permanently failed
        self.times = 0          # number of submissions

def fetch_pending_rows(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT rowid, country, city, education_level
        FROM ccas_city
        WHERE ccas_status IS NULL OR TRIM(ccas_status) = ''
    """)
    rows = cur.fetchall()
    jobs = [
        Job(
            rowid=row["rowid"],
            country=row["country"],
            city=row["city"],
            education_level=row["education_level"]
        )
        for row in rows
    ]
    return deque(jobs)  # FIFO queue

def submit_job(job):
    response = client.responses.create(
        model="o3-deep-research",
        input=prompt_gen(job.country, job.city, job.education_level),
        background=True,
        tools=[{"type": "web_search_preview"}],
    )
    job.job_id = response.id
    job.submitted_at = datetime.now()
    job.times += 1
    print(f"Submitted job_id={job.job_id} for {job.country}, {job.city}, {job.education_level} (attempt {job.times})")
    return job


def poll_result(job):
    try:
        result = client.responses.retrieve(job.job_id)
        status = result.status
        elapsed = datetime.now() - job.submitted_at
        print(f"Polling job_id={job.job_id}: status={status}, elapsed={elapsed}, country={job.country}, city={job.city}, education_level={job.education_level}")

        if status in ("succeeded", "completed"):
            print(result.output_text)
            try:
                return True, json.loads(result.output_text)
            except json.JSONDecodeError:
                # clean markdown backticks
                try:
                    json_text = re.sub(r"^```(?:json)?\s*", "", result.output_text.strip(), flags=re.IGNORECASE)
                    json_text = re.sub(r"\s*```$", "", json_text)
                    return True, json.loads(json_text)
                except json.JSONDecodeError:
                    print("Model did not return valid JSON")
                    return False, None
        elif status in ("failed", "cancelled") or elapsed > timedelta(minutes=JOB_TIMEOUT_MINUTES):
            return False, None
        else:  # pending / processing
            return None, None
    except Exception as e:
        print(f"Error polling job {job.job_id}: {e}")
        return False, None

def to_text(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)

def save_result(conn, job, json_output):
    cur = conn.cursor()
    cur.execute("""
        UPDATE ccas_city
        SET ccas_status = ?,
            ccas_status_source = ?,
            participating_institutions = ?,
            participating_institutions_source = ?,
            preference_list_length = ?,
            preference_list_length_source = ?,
            priority_criteria = ?,
            priority_criteria_source = ?,
            assignment_mechanism = ?,
            assignment_mechanism_source = ?,
            adoption_year = ?,
            adoption_year_source = ?,
            reform_year = ?,
            reform_year_source = ?,
            notes = ?
        WHERE rowid = ?
    """, (
        to_text(json_output.get("ccas_status")),
        to_text(json_output.get("ccas_status_source")),
        to_text(json_output.get("participating_institutions")),
        to_text(json_output.get("participating_institutions_source")),
        to_text(json_output.get("preference_list_length")),
        to_text(json_output.get("preference_list_length_source")),
        to_text(json_output.get("priority_criteria")),
        to_text(json_output.get("priority_criteria_source")),
        to_text(json_output.get("assignment_mechanism")),
        to_text(json_output.get("assignment_mechanism_source")),
        to_text(json_output.get("adoption_year")),
        to_text(json_output.get("adoption_year_source")),
        to_text(json_output.get("reform_year")),
        to_text(json_output.get("reform_year_source")),
        to_text(json_output.get("notes")),
        job.rowid
    ))
    conn.commit()
    print(f"Updated DB for {job.country}, {job.city}, {job.education_level}")

def process_jobs(conn, job_queue):
    while job_queue:
        job = job_queue.popleft()  # FIFO
        if job.completed or job.failed:
            continue  # skip already finished jobs
        try:
            # Submit job if not yet submitted or needs retry
            if job.job_id is None and job.times < MAX_RETRIES:
                submit_job(job)
                job_queue.append(job)
                time.sleep(POLL_INTERVAL)
                continue

            done, json_output = poll_result(job)

            if done is True and json_output:
                save_result(conn, job, json_output)
                job.completed = True
            elif done is False:  # failed or timeout
                if job.times < MAX_RETRIES:
                    print(f"Retrying job for {job.country}, {job.city}, {job.education_level}")
                    job.job_id = None  # reset to resubmit
                    job_queue.append(job)
                else:
                    print(f"Max retries reached for {job.country}, {job.city}, {job.education_level}")
                    job.failed = True
            else:  # still pending
                job_queue.append(job)
        except Exception as e:
            print(f"Exception for {job.country}, {job.city}, {job.education_level}: {e}")
            if job.times < MAX_RETRIES:
                job.job_id = None
                job_queue.append(job)
            else:
                job.failed = True
        time.sleep(POLL_INTERVAL)
        # Return the number of unfinished jobs left in the queue
        unfinished_jobs = sum(1 for x in job_queue if not x.completed and not x.failed)
        failed_jobs = sum(x.failed for x in job_queue)
        print(f"{unfinished_jobs} jobs left in the queue, {failed_jobs} failed jobs")

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    job_queue = fetch_pending_rows(conn)
    print(f"Found {len(job_queue)} jobs to process")

    process_jobs(conn, job_queue)
    conn.close()

if __name__ == "__main__":
    main()
