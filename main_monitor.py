import time
import monitor_net
import monitor_pi
import os
import send_telegram

OFFLINE_LOG = "offline_log.txt"
COOLDOWN = 3600

warnings_states = {
    "router_down": False,
    "internet_down": False,
    "pi_hot": False,
    "pi_ram": False,
    "last_warning" : 0.0
}

segundos_red = 0
segundos_pi = 0

print(f"MAIN_MONITOR IS RUNNING")

while True:

    print(f"* Second: {segundos_red}")

    if segundos_red >= 30:

        net_report = monitor_net.report()

        print(f"----------Network script runned successfully----------")

        if net_report["status_router"] != "online":

            print("Router is offline...")
            print(f"Past Status: ", end="")
            if warnings_states["router_down"]: print("Offline")
            else: print("Online\nReport due.")

            if not warnings_states["router_down"]:

                pi = monitor_pi.report()

                with open(OFFLINE_LOG, "w") as f:
                    f.write(str(f"""
                    Router is down.
                    
                    Loss: {net_report['packet_loss_router']:.1f}%
                    Jitter: {net_report['jitter_router']:.1f} ms
                    Total queries: {net_report['dns_number_queries']}
                    Pi's State:
                    Ram usage: {pi["ram_usage"]:.1f}
                    Temperature: {pi["temperature"]:.1f}
                    """))

                warnings_states["router_down"] = True

                print("Saved in logs.")

        elif net_report["status_internet"] != "online":

            print(f"Internet is down.")
            print(f"Past Status: ", end="")
            if warnings_states["internet_down"]:
                print("Offline")
            else:
                print("Online\nReport due.")

            if not warnings_states["internet_down"]:
                pi = monitor_pi.report()

                with open(OFFLINE_LOG, "w") as f:
                    f.write(f"""
                    Router is working, but has no internet.
                    
                    Total queries: {net_report['dns_number_queries']}
                    Pi's State:
                    Ram usage: {pi["ram_usage"]:.1f}%
                    Temperature: {pi["temperature"]:.1f}
                    """)

                warnings_states["internet_down"] = True

                print("Saved in logs.")

        else:

            if os.path.exists(OFFLINE_LOG):
                print("Internet is back. Uploading logs.")

                with open(OFFLINE_LOG, "r") as f:
                    saved_logs = f.read()

                logs_message = f"""*INTERNET IS BACK*
                This is the report:
                {saved_logs}
                """

                send_telegram.send_message(logs_message)
                os.remove(OFFLINE_LOG)

            warnings_states["internet_down"] = False
            warnings_states["router_down"] = False

            small_notifs = []

            if net_report["jitter_router"] > monitor_net.MAX_JITTER:
                small_notifs.append("High jitter")

            if net_report["packet_loss_router"] > monitor_net.MAX_PACKET_LOSS:
                small_notifs.append("High packet loss")

            if net_report["dns_number_queries"] > monitor_net.MAX_DNS_QUERIES:
                small_notifs.append("High DNS queries")

            if small_notifs:

                print(f"Anomalies were found in the network. Incomming report: {small_notifs}")

                current_time = time.time()
                passed_time = current_time - warnings_states["last_warning"]

                if passed_time >= COOLDOWN:
                    pi = monitor_pi.report()

                    overview = "\n".join(small_notifs)

                    telegram_message = f"""

                            **NETWORK WARNING**

                            **Warning reason(s):**
                            {overview}

                            **Complete network metrics:**
                            *Local Router*
                            Status: {net_report['status_router']}
                            Loss: {net_report['packet_loss_router']}%
                            Jitter: {net_report['jitter_router']:.2f} ms

                            *Internet (8.8.8.8):*
                            Status: {net_report['status_google']}
                            Loss: {net_report['packet_loss_google']}%
                            Jitter: {net_report['jitter_google']:.2f} ms

                            *Pi-hole (Last 5 min. traffic):*
                            Total queries: {net_report['dns_number_queries']}

                            ---
                            *Pi Status:*
                            RAM in use: {pi["ram_usage"]:.1f}%
                            Temperature: {pi["temperature"]:.1f} °C
                            """

                    send_telegram.send_message(telegram_message)

                    warnings_states["last_warning"] = current_time

                else:
                    print(f"Network reports are on cooldown.")
                    pass

        segundos_red = 0

    if segundos_pi >= 600:

        if not warnings_states["internet_down"] and not warnings_states["router_down"]:
            pi = monitor_pi.report()

            notifs = []

            if pi["ram_usage"] > monitor_pi.MAX_RAM:
                if not warnings_states["pi_hot"]:
                    notifs.append(f"*RAM in use:* {pi['ram_usage']:.1f}%")
                    warnings_states["pi_ram"] = True
            else:
                warnings_states["pi_ram"] = False

            if pi["temperature"] > monitor_pi.MAX_TEMP:
                if not warnings_states["pi_hot"]:
                    notifs.append(f"*Temperature:* {pi['temperature']:.1f} °C")
                    warnings_states["pi_hot"] = True
            else:
                warnings_states["pi_hot"] = False

            if notifs:

                print(f"High hardware values on the raspberry Pi. Reporting: {notifs}")

                message = f"*[HARDWARE ALERT - RASPBERRY PI]*\n"

                for anomaly in notifs:
                    message += f"• {anomaly}\n"

                send_telegram.send_message(message)

        segundos_pi = 0

    time.sleep(1)
    segundos_red += 1
    segundos_pi += 1