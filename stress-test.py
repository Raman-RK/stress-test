import time
import random
import logging
import multiprocessing
import undetected_chromedriver as uc
import csv
import os

# === CONFIGURATION ===
URL = "https://meetn.com/testmodestart"
NUM_HITS = 1000
BATCH_SIZE = 20  # Lowered to avoid memory overload
TOTAL_TIMEOUT = 1800  # 30 minutes timeout

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0"
]

# === LOGGING SETUP ===
logging.basicConfig(
    filename="stress_test.log",
    level=logging.INFO,
    format="%(asctime)s - Hit#%(hit)d - %(levelname)s - %(message)s"
)

CSV_FILE = "successful_hits.csv"

def write_to_csv(result):
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["hit", "duration", "user_agent", "captcha", "status"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(result)


def launch_browser(hit_num):
    logger = logging.LoggerAdapter(logging.getLogger(), {'hit': hit_num})

    try:
        logger.info("Launching browser")

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
        time.sleep(random.uniform(0.2, 0.5))
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

        write_to_csv(result)
        logger.info(f"Completed in {load_duration:.2f}s | CAPTCHA: {captcha_detected}")

    except Exception as e:
        logger.error(f"Failed: {e}")
        result = {
            "hit": hit_num,
            "duration": 0,
            "user_agent": "N/A",
            "captcha": False,
            "status": "Failed"
        }
        write_to_csv(result)


def run_batch(start_hit, end_hit):
    processes = []
    for hit_num in range(start_hit, end_hit):
        p = multiprocessing.Process(target=launch_browser, args=(hit_num,))
        p.start()
        processes.append(p)

    for p in processes:
        p.join(timeout=TOTAL_TIMEOUT / NUM_HITS * BATCH_SIZE)  # give each batch limited time


if __name__ == "__main__":
    multiprocessing.freeze_support()

    total_start_time = time.time()
    total_batches = (NUM_HITS + BATCH_SIZE - 1) // BATCH_SIZE

    if os.path.exists(CSV_FILE):
        os.remove(CSV_FILE)  # fresh start

    for batch_num in range(total_batches):
        batch_start = batch_num * BATCH_SIZE + 1
        batch_end = min((batch_num + 1) * BATCH_SIZE + 1, NUM_HITS + 1)

        run_batch(batch_start, batch_end)

        elapsed = time.time() - total_start_time
        if elapsed > TOTAL_TIMEOUT:
            print("⏳ Global timeout exceeded. Stopping.")
            break

    total_end_time = time.time()
    print(f"\n✅ Finished in {round(total_end_time - total_start_time, 2)} seconds!")
    print(f"📄 Results saved to '{CSV_FILE}'")
