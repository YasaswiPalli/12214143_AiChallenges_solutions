import time
import json
import logging
from fastapi.testclient import TestClient
from app.main import app, jobs

client = TestClient(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestRun")

def run_tests():
    logger.info("Starting API tests...")
    
    # Load test payload
    with open("test_req.json", "r") as f:
        payload = json.load(f)

    logger.info(f"Test payload: {payload}")

    # 1. Test Generate Endpoint
    response = client.post("/generate-storyboard", json=payload)
    if response.status_code != 202:
        logger.error(f"Failed to submit job. Status: {response.status_code}, Body: {response.text}")
        return False
    
    data = response.json()
    job_id = data.get("job_id")
    logger.info(f"Job submitted successfully. Job ID: {job_id}")

    # 2. Poll Status Endpoint
    max_retries = 30
    delay = 2
    for i in range(max_retries):
        status_res = client.get(f"/status/{job_id}")
        if status_res.status_code != 200:
            logger.error(f"Failed to get status. Status: {status_res.status_code}")
            return False
            
        status_data = status_res.json()
        logger.info(f"Polling ({i+1}/{max_retries}): {status_data['status']} - {status_data['progress']}%")
        
        if status_data["status"] == "completed":
            break
        elif status_data["status"] == "failed":
            logger.error(f"Job failed! Error: {status_data.get('error')}")
            return False
            
        time.sleep(delay)
    
    if status_data["status"] != "completed":
        logger.error("Job did not complete in time.")
        return False

    # 3. Test Storyboard JSON Endpoint
    json_res = client.get(f"/storyboard/{job_id}/json")
    if json_res.status_code != 200:
        logger.error(f"Failed to get storyboard JSON. Status: {json_res.status_code}")
        return False
        
    storyboard_data = json_res.json()
    scenes = storyboard_data.get("scenes", [])
    
    logger.info(f"Total scenes generated: {len(scenes)}")
    
    # Validate Core Requirements
    if len(scenes) < 3:
        logger.error("Failed Req 2: Did not generate at least 3 scenes.")
        return False
        
    for idx, scene in enumerate(scenes):
        original = scene["original_text"]
        prompt = scene["engineered_prompt"]
        image = scene["image_data_uri"]
        logger.info(f"Scene {idx+1}:")
        logger.info(f"  Original: {original}")
        logger.info(f"  Enhanced Prompt: {prompt}")
        logger.info(f"  Image Data URI exists: {bool(image)}")
        
        if original == prompt:
            logger.error(f"Failed Req 3: Original text was not enhanced. ({original})")
            return False
        if not image:
            logger.error(f"Failed Req 4: Image was not generated.")
            return False

    # 4. Test HTML Endpoint
    html_res = client.get(f"/storyboard/{job_id}")
    if html_res.status_code != 200:
        logger.error(f"Failed to get storyboard HTML. Status: {html_res.status_code}")
        return False
    
    logger.info("All tests passed successfully! API works as expected and satisfies all core requirements.")
    return True

if __name__ == "__main__":
    success = run_tests()
    if not success:
        exit(1)
