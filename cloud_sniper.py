import asyncio
import httpx
import os
import json

GRAPHQL_URL = "https://e5mquma77feepi2bdn4d6h3mpu.appsync-api.us-east-1.amazonaws.com/graphql"
LOCATION_LAT = 43.7315
LOCATION_LNG = -79.7624

def load_token():
    with open("token.txt", "r") as f:
        return f.read().strip()

def build_headers():
    return {
        "Authorization": load_token(),
        "Content-Type": "application/json",
        "Origin": "https://hiring.amazon.ca",
        "Referer": "https://hiring.amazon.ca/",
        "User-Agent": "Mozilla/5.0"
    }

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

async def send_to_home(job_id, schedule_id):
    home_url = os.getenv("HOME_RECEIVER_URL", "http://localhost:5000/apply")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(home_url, json={"jobId": job_id, "scheduleId": schedule_id})
            print(f"[🚀] Sent to home: {job_id} | {schedule_id} | {res.status_code}")
    except Exception as e:
        print(f"[❌] Failed to send: {e}")

async def poll():
    print("[🔍] Cloud Sniper watching...")
    async with httpx.AsyncClient(http2=True, timeout=5.0) as client:
        while True:
            try:
                job_res = await client.post(GRAPHQL_URL, headers=build_headers(), json=build_job_query())
                job_cards = job_res.json()["data"]["searchJobCardsByLocation"]["jobCards"]

                schedule_tasks = [
                    client.post(GRAPHQL_URL, headers=build_headers(), json=build_schedule_query(job["jobId"]))
                    for job in job_cards
                ]
                schedule_responses = await asyncio.gather(*schedule_tasks, return_exceptions=True)

                for job, sched_res in zip(job_cards, schedule_responses):
                    if isinstance(sched_res, Exception):
                        continue
                    schedules = sched_res.json()["data"]["searchScheduleCards"]["scheduleCards"]
                    for sched in schedules:
                        if sched.get("laborDemandAvailableCount", 0) > 0:
                            await send_to_home(sched["jobId"], sched["scheduleId"])
                            await asyncio.sleep(3)

                await asyncio.sleep(0.3)

            except Exception as e:
                print(f"[ERROR] {e}")
                await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(poll())
