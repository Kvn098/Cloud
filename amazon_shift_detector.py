import asyncio
import httpx
import json
import os
from datetime import datetime
import pyttsx3



# -----------------------
# CONFIGURATION
# -----------------------

GRAPHQL_URL = "https://e5mquma77feepi2bdn4d6h3mpu.appsync-api.us-east-1.amazonaws.com/graphql"
AUTHORIZATION = "Bearer Status|logged-in|Session|eyJhbGciOiJLTVMiLCJ0eXAiOiJKV1QifQ.eyJpYXQiOjE3NDg1MzM2MTMsImV4cCI6MTc0ODUzNzIxM30.AQICAHidzPmCkg52ERUUfDIMwcDZBDzd+C71CJf6w0t6dq2uqwHgZCNCUYtjVMCYLsmFq/eDAAAAtDCBsQYJKoZIhvcNAQcGoIGjMIGgAgEAMIGaBgkqhkiG9w0BBwEwHgYJYIZIAWUDBAEuMBEEDImZZzaYiNX47WvYnwIBEIBtRW5zNT2G8tFyWLOAJ6SfsA/9BUfLzUZJskveL3XGTghuk28rKeOfxb4FgQC87oBYcGvYaL8kIJh0ynNi/AQe1rAbVPX0/6oIjPKOlJsSLYAr1m1wm8pht5u08KFpUlDKcg4wKK+LqD4XoGVTyQ=="  # <-- Use your actual token
HEADERS = {
    "Authorization": AUTHORIZATION,
    "Content-Type": "application/json",
    "Origin": "https://hiring.amazon.ca",
    "Referer": "https://hiring.amazon.ca/",
    "User-Agent": "Mozilla/5.0"
}
LOCATION_LAT = 43.7315
LOCATION_LNG = -79.7624

BASE_DIR = r"D:\DirectCreateApp"
JOB_DATA_FILE = os.path.join(BASE_DIR, "job_data.json")
WAIT_BETWEEN_SHIFTS = 2.0  # Wait after each job_data write (redirect + click time)

last_written = None

# -----------------------
# ALERT
# -----------------------

def alert_shift():
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 170)
        engine.say("Shift detected. Job page is open.")
        engine.runAndWait()
    except Exception as e:
        print(f"[🗣️] Voice alert failed: {e}")

    

# -----------------------
# UTILITIES
# -----------------------

def write_job_data(job_id, schedule_id):
    global last_written
    current = (job_id, schedule_id)

    if current == last_written:
        return  # 🔁 skip repeated write (same shift again)

    data = {"jobId": job_id, "scheduleId": schedule_id}
    with open(JOB_DATA_FILE, "w") as f:
        json.dump(data, f)
    last_written = current
    print(f"[📁] Wrote job_data.json → {job_id} | {schedule_id} @ {datetime.now().strftime('%H:%M:%S')}")
    alert_shift()

def build_job_query():
    return {
        "operationName": "searchJobCardsByLocation",
        "query": """
            query searchJobCardsByLocation($searchJobRequest: SearchJobRequest!) {
              searchJobCardsByLocation(searchJobRequest: $searchJobRequest) {
                jobCards {
                  jobId
                  jobTitle
                  locationName
                }
              }
            }
        """,
        "variables": {
            "searchJobRequest": {
                "locale": "en-CA",
                "country": "Canada",
                "containFilters": [{"key": "isPrivateSchedule", "val": ["false"]}],
                "geoQueryClause": {
                    "lat": LOCATION_LAT,
                    "lng": LOCATION_LNG,
                    "unit": "km",
                    "distance": 200
                },
                "pageSize": 100
            }
        }
    }

def build_schedule_query(job_id):
    return {
        "operationName": "searchScheduleCards",
        "query": """
            query searchScheduleCards($searchScheduleRequest: SearchScheduleRequest!) {
              searchScheduleCards(searchScheduleRequest: $searchScheduleRequest) {
                scheduleCards {
                  scheduleId
                  jobId
                  firstDayOnSite
                  laborDemandAvailableCount
                }
              }
            }
        """,
        "variables": {
            "searchScheduleRequest": {
                "locale": "en-CA",
                "country": "Canada",
                "rangeFilters": [{"key": "hoursPerWeek", "range": {"minimum": 0, "maximum": 80}}],
                "containFilters": [{"key": "isPrivateSchedule", "val": ["false"]}],
                "sorters": [{"fieldName": "totalPayRateMax", "ascending": "false"}],
                "pageSize": 1000,
                "consolidateSchedule": True,
                "jobId": job_id
            }
        }
    }

# -----------------------
# MAIN LOOP
# -----------------------

async def poll_jobs():
    async with httpx.AsyncClient(http2=True, timeout=5.0) as client:
        print("[🔍] Shift watcher running...")

        while True:
            try:
                res = await client.post(GRAPHQL_URL, headers=HEADERS, json=build_job_query())
                job_cards = res.json()["data"]["searchJobCardsByLocation"]["jobCards"]

                schedule_tasks = [
                    client.post(GRAPHQL_URL, headers=HEADERS, json=build_schedule_query(job["jobId"]))
                    for job in job_cards
                ]
                schedule_responses = await asyncio.gather(*schedule_tasks, return_exceptions=True)

                shifts = []
                for job, response in zip(job_cards, schedule_responses):
                    if isinstance(response, Exception):
                        continue
                    schedules = response.json()["data"]["searchScheduleCards"]["scheduleCards"]
                    for sched in schedules:
                        if sched.get("laborDemandAvailableCount", 0) > 0:
                            shifts.append((job, sched))

                for job, sched in shifts:
                    job_id = sched["jobId"]
                    schedule_id = sched["scheduleId"]
                    print(f"[✅] Applying: {job['jobTitle']} — {job['locationName']} — Schedule {schedule_id}")
                    await asyncio.to_thread(write_job_data, job_id, schedule_id)
                    await asyncio.sleep(WAIT_BETWEEN_SHIFTS)

                await asyncio.sleep(0.25)

            except Exception as e:
                print(f"[❌] Error: {e}")
                await asyncio.sleep(2)

# -----------------------
# ENTRY
# -----------------------

if __name__ == "__main__":
    asyncio.run(poll_jobs())
