import concurrent.futures
import os
import random

import requests

from database import connect_to_db

# Proxy settings
PROXY_API_KEY = os.getenv("PROXY_API_KEY")
PROXY_API_URL = f"https://api.best-proxies.ru/proxylist.json?key={PROXY_API_KEY}&limit=0"

# Scoring coefficients
ALPHA = 0.5  # Weight for the old score
BETA = 0.5  # Penalty factor for failed requests
SPEED_WEIGHT = 0.5
RELIABILITY_WEIGHT = 0.3
USAGE_WEIGHT = 0.2
MAX_RESPONSE_TIME = 10.0  # Maximum response time in seconds


# Function to fetch proxies from the API
def fetch_proxies(conn):
    try:
        response = requests.get(PROXY_API_URL)
        response.raise_for_status()
        proxies = response.json()
        save_proxies_to_db(proxies, conn)
        return proxies
    except requests.RequestException as e:
        print(f"Failed to fetch proxies: {e}")
        return []


# Function to save proxies to the database
def save_proxies_to_db(proxies, conn):
    try:
        cur = conn.cursor()
        for proxy in proxies:
            ip = proxy["ip"]
            port = proxy["port"]
            real_ip = proxy.get("real_ip", ip)  # Default to IP if real_ip is not provided
            response_time = proxy.get("response", 0)
            good_count = proxy.get("good_count", 0)
            bad_count = proxy.get("bad_count", 0)

            for protocol in ["http", "https", "socks4", "socks5"]:
                if proxy.get(protocol) == 1:
                    try:
                        cur.execute(
                            """
                INSERT INTO proxies (ip, port, protocol, real_ip, score, good_count, bad_count, response, used_count)
                            VALUES (%s, %s, %s, %s, 0.5, %s, %s, %s, 0)
                            ON CONFLICT (ip, port, protocol) DO NOTHING;
                            """,
                            (ip, port, protocol, real_ip, good_count, bad_count, response_time),
                        )
                    except Exception as e:
                        print(f"Error inserting proxy {ip}:{port} ({protocol}): {e}")
        conn.commit()
        print("Proxies saved to database.")
    except Exception as e:
        print(f"Error saving proxies to database: {e}")
    finally:
        cur.close()


# Function to check proxy validity and score it
def check_and_score_proxy(proxy):
    test_url = "https://httpbin.org/ip"
    proxy_url = f"{proxy['protocol']}://{proxy['ip']}:{proxy['port']}"

    try:
        response = requests.get(test_url, proxies={"http": proxy_url, "https": proxy_url}, timeout=5)
        response.raise_for_status()
        response_time = response.elapsed.total_seconds()

        speed_factor = 1 - min(1, response_time / MAX_RESPONSE_TIME)
        reliability_factor = proxy["good_count"] / (proxy["good_count"] + proxy["bad_count"] + 1)
        usage_factor = 1 - min(1, proxy["used_count"] / 10)

        calc_score = SPEED_WEIGHT * speed_factor + RELIABILITY_WEIGHT * reliability_factor + USAGE_WEIGHT * usage_factor
        old_score = proxy.get("score", 0)

        # Update the score with inertia
        new_score = ALPHA * old_score + (1 - ALPHA) * calc_score

        print(
            f"Proxy {proxy_url} scored {new_score:.2f}. Old score: {old_score:.2f}, Calculated score: {calc_score:.2f}."
        )
        return new_score, response_time
    except requests.RequestException:
        print(f"Proxy {proxy_url} is invalid.")
        old_score = proxy.get("score", 0)
        new_score = BETA * old_score
        print(f"Proxy {proxy_url} failed. Old score: {old_score:.2f}, New score: {new_score:.2f}.")
        return new_score, None


# Function to update a single proxy in the database
def update_proxy_score(proxy_dict, conn):
    try:
        # Use the score as a probability to decide if the proxy is checked
        if random.random() > proxy_dict["score"]:
            return

        cur = conn.cursor()
        score, response_time = check_and_score_proxy(proxy_dict)

        if response_time is not None:
            cur.execute(
                """
                UPDATE proxies
                SET score = %s, response = %s, good_count = good_count + 1, last_checked = CURRENT_TIMESTAMP
                WHERE id = %s;
                """,
                (score, response_time, proxy_dict["id"]),
            )
        else:
            cur.execute(
                """
                UPDATE proxies
                SET score = %s, bad_count = bad_count + 1, last_checked = CURRENT_TIMESTAMP
                WHERE id = %s;
                """,
                (score, proxy_dict["id"]),
            )
        conn.commit()
    except Exception as e:
        print(f"Error updating proxy {proxy_dict['ip']}:{proxy_dict['port']}: {e}")
    finally:
        cur.close()


# Function to process proxies in a loop with concurrency
def process_proxies_concurrently():
    conn = connect_to_db()
    if conn is None:
        return

    try:
        while True:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, ip, port, protocol, real_ip, good_count, bad_count, used_count, score, last_checked
                FROM proxies
                ORDER BY last_checked ASC;
            """
            )
            proxies = cur.fetchall()

            proxies_list = [
                {
                    "id": proxy[0],
                    "ip": proxy[1],
                    "port": proxy[2],
                    "protocol": proxy[3],
                    "real_ip": proxy[4],
                    "good_count": proxy[5],
                    "bad_count": proxy[6],
                    "used_count": proxy[7],
                    "score": proxy[8],
                }
                for proxy in proxies
            ]

            with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
                executor.map(lambda proxy: update_proxy_score(proxy, conn), proxies_list)

            fetch_proxies(conn)
    except Exception as e:
        print(f"Error processing proxies: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    process_proxies_concurrently()
