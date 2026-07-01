import re
import sqlite3
import subprocess
import send_telegram
import monitor_pi
import time

ROUTER_IP = "192.168.0.1"
GOOGLE_IP = "8.8.8.8"
MAX_JITTER = 15.0
MAX_PACKET_LOSS = 20.0
MAX_DNS_QUERIES = 300
PIHOLE_DB = "/etc/pihole/pihole-FTL.db"

def analyze_ping_and_jitter(ip: str, count: int = 5) -> dict:

    command = ["ping", "-c", str(count), ip]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )

        print(f"Pinging {ip}...")

        if result.returncode != 0:
            print(f"Error: Could not ping {ip}")

            return {
                "status": "error",
                "packet_loss": 100.0,
                "jitter": 0.0
            }

        console_text = result.stdout

        time_logs = [float(t) for t in re.findall(r"time=([0-9.]+)", console_text)]

        print(f"Presenting time logs:\n{time_logs}")

        if not time_logs:
            print(f"No time logs found for {ip}")
            return {
                "status": "offline",
                "packet_loss": 100.0,
                "jitter": 0.0
            }

        difference =[]

        for logs in range(len(time_logs) - 1):
            dif = abs(time_logs[logs + 1] - time_logs[logs])
            difference.append(dif)

        print(f"Presenting difference of logs for {ip}:\n{difference}")

        jitter = sum(difference) / len(difference)

        received_packages = len(time_logs)

        packet_loss = ((count - received_packages) / count) * 100

        print(
            f"""Analyze success. Results to be logged and uploaded:
            "status": "online",
            "packet_loss": {packet_loss},
            "jitter": {jitter},
            "raw_logs": {time_logs}
            
            """)

        return {
            "status": "online",
            "packet_loss": packet_loss,
            "jitter": jitter,
            "raw_logs": time_logs
        }

    except subprocess.TimeoutExpired:
        print(f"Pinging to {ip}: Timeout Expired")
        return {
            "status": "offline",
            "packet_loss": 0.0,
            "jitter": 0.0,
        }

def get_pihole_traffic(minutes: int = 5) -> int:

    print(f"||||||Measuring PiHole traffic||||||")

    x_minutes_ago = int(time.time() - (minutes * 60))

    query = "SELECT COUNT(*) FROM queries WHERE timestamp > ?;"

    connect = None

    try:

        connect = sqlite3.connect(PIHOLE_DB)
        cursor = connect.cursor()

        cursor.execute(query, (x_minutes_ago,))

        result = cursor.fetchone()
        total_petitions = result[0] if result else 0

        print(f"Successfully compiled PiHole's data: Total Petitions: {total_petitions}")

        return total_petitions

    except sqlite3.OperationalError as e:
        print(f"Something went wrong when entering PiHole database: {e}")
        return 0

    finally:
        if connect:
            connect.close()

def report():

    print("report of network running...")

    router = analyze_ping_and_jitter(ROUTER_IP)
    google = analyze_ping_and_jitter(GOOGLE_IP)
    dns_count = get_pihole_traffic()

    return {
        "status_router": router["status"],
        "packet_loss_router": router["packet_loss"],
        "jitter_router": router["jitter"],
        "status_google": google["status"],
        "packet_loss_google": google["packet_loss"],
        "jitter_google": google["jitter"],
        "dns_number_queries": dns_count,
    }

if __name__ == '__main__':

    report_final = report()

    notifs = []

    if report_final["status_router"] != "online":
        notifs.append("Router is not working")

    if report_final["packet_loss_router"] > MAX_PACKET_LOSS:
        notifs.append("High packet loss")

    if report_final["jitter_router"] > MAX_JITTER:
        notifs.append("High jitter")

    if report_final["status_google"] != "online":
        notifs.append("No connection to internet")

    if report_final["dns_number_queries"] > MAX_DNS_QUERIES:
        notifs.append("Anomaly high DNS queries")

    if notifs:

        pi_report = monitor_pi.report()

        overview = "\n".join(notifs)

        telegram_message = f"""
        
        **NETWORK WARNING**
        
        **Warning reason(s):**
        {overview}
        
        **Complete network metrics:**
        *Local Router*
        Status: {report_final['status_router']}
        Loss: {report_final['packet_loss_router']}%
        Jitter: {report_final['jitter_router']:.2f} ms

        *Internet (8.8.8.8):*
        Status: {report_final['status_google']}
        Loss: {report_final['packet_loss_google']}%
        Jitter: {report_final['jitter_google']:.2f} ms

        *Pi-hole (Last 5 min. traffic):*
        Total queries: {report_final['dns_number_queries']}
        
        ---
        *Pi Status:*
        RAM in use: {pi_report["ram_usage"]:.1f}%
        Temperature: {pi_report["temperature"]:.1f} °C
        """

        send_telegram.send_message(telegram_message)
