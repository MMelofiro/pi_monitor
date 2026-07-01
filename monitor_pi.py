import send_telegram

MAX_TEMP = 75.0          # Max temperature threshold in Celsius
MAX_RAM = 90.0           # Max percentage threshold

def get_temperature():
    """
    Reads temperature of the pi.

    Returns:
        float: Temperature in Celsius
    """
    path = "/sys/class/thermal/thermal_zone0/temp"

    print(f"Getting temperature from pi")

    try:
        with open(path, "r") as file:
            content = file.read()

        temp_c = float(content) / 1000

        print(f"Sucessfully read temperature from pi: {temp_c:.2f} °C")

        return temp_c

    except FileNotFoundError:
        print("Error reading temperature from pi")
        return 0

def get_ram_usage():
    """
    Calculates ram usage of the pi in percent.

    Returns:
        float: Percent of ram in use
    """
    path = "/proc/meminfo"

    print(f"Getting ram usage from pi")

    try:
        with open(path, "r") as file:
            for line in file:
                if "MemAvailable" in line:
                    mem_av_kb = int(line.split()[1])
                if "MemTotal" in line:
                    mem_tot_kb = int(line.split()[1])

        mem_in_use_percentage = ((mem_tot_kb - mem_av_kb) / mem_tot_kb) * 100

        print(f"Successfully read ram usage from pi: {mem_in_use_percentage:.2f} %")

        return mem_in_use_percentage

    except FileNotFoundError:
        print("Error reading ram usage from pi")
        return 0

def report():
    """
    :return: dictionary with the methods that measure hardware status.
    """

    print(f"Report of pi running...")

    return{
        "ram_usage": get_ram_usage(),
        "temperature": get_temperature()
    }

if __name__ == "__main__":

    data = report()

    notifs = []

    if data["ram_usage"] > MAX_RAM:
        notifs.append(f"*RAM in use:* {data['ram_usage']:.1f}%")

    if data["temperature"] > MAX_TEMP:
        notifs.append(f"*Temperature:* {data['temperature']:.1f} °C")

    if notifs:

        message = f"*[HARDWARE ALERT - RASPBERRY PI]*\n"

        for anomaly in notifs:
            message += f"• {anomaly}\n"

        send_telegram.send_message(message)