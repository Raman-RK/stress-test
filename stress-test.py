import time
import random
import logging
import multiprocessing
import undetected_chromedriver as uc
import csv

# === CONFIGURATION ===
URL = "https://meetn.com/testmodestart"
NUM_HITS = 1000
BATCH_SIZE = 20
TOTAL_TIMEOUT = 60  # Seconds

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0"
]

# === LOGGING SETUP ===
logging.basicConfig(
    filename="stress_test.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

def launch_browser(hit_num, results):
    try:
        logger.info(f"Launching browser | Hit #{hit_num}")

        options = uc.ChromeOptions()
        options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")

        driver = uc.Chrome(options=options, version_main=135)
        driver.set_page_load_timeout(20)

        start_time = time.time()
        driver.get(URL)
        time.sleep(random.uniform(0.2, 0.5))  # small wait after page load
        load_duration = time.time() - start_time

        page_source = driver.page_source.lower()
        page_title = driver.title.lower()
        captcha_detected = "captcha" in page_source or "are you human" in page_title

        driver.quit()

        result = {
            "hit": hit_num,
            "duration": round(load_duration, 2),
            "user_agent": options.arguments[-1],
            "captcha": captcha_detected,
            "status": "CaptchaTriggered" if captcha_detected else "Success"
        }
        results.append(result)

        logger.info(f"Completed Hit #{hit_num} in {load_duration:.2f}s | CAPTCHA: {captcha_detected}")

    except Exception as e:
        logger.error(f"Hit #{hit_num} Failed: {e}")
        results.append({
            "hit": hit_num,
            "status": "Failed",
            "error": str(e)
        })

def run_batch(start_hit, end_hit, results):
    processes = []
    for hit_num in range(start_hit, end_hit):
        p = multiprocessing.Process(target=launch_browser, args=(hit_num, results))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

if __name__ == "__main__":
    multiprocessing.freeze_support()  # Needed for Windows multiprocessing

    manager = multiprocessing.Manager()
    results = manager.list()

    total_start_time = time.time()

    total_batches = (NUM_HITS + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_num in range(total_batches):
        batch_start = batch_num * BATCH_SIZE + 1
        batch_end = min((batch_num + 1) * BATCH_SIZE + 1, NUM_HITS + 1)

        run_batch(batch_start, batch_end, results)

        elapsed = time.time() - total_start_time
        if elapsed > TOTAL_TIMEOUT:
            print("⏳ Timeout exceeded. Stopping early.")
            break

    total_end_time = time.time()

    # === SUMMARY ===
    success_count = sum(1 for r in results if r["status"] == "Success")
    captcha_count = sum(1 for r in results if r["status"] == "CaptchaTriggered")
    failure_count = sum(1 for r in results if r["status"] == "Failed")

    print("\n====== SUMMARY ======")
    print(f"Total Attempts: {len(results)}")
    print(f"Successful (no CAPTCHA): {success_count}")
    print(f" CAPTCHA Triggered: {captcha_count}")
    print(f"Failed Attempts: {failure_count}")
    print(f"Total Time: {round(total_end_time - total_start_time, 2)} seconds")
    print(f"Logs saved in 'stress_test.log'.")

    # === SAVE SUCCESSFUL HITS ===
    with open("successful_hits.csv", "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["hit", "duration", "user_agent", "captcha", "status"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for r in results:
            if r["status"] in ["Success", "CaptchaTriggered"]:
                writer.writerow(r)

    print("\nResults saved in 'successful_hits.csv'.")
