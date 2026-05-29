import requests


def run_bhunaksha_plot_info_demo() -> None:
    url = "https://upbhunaksha.gov.in/bhunakshaserver/MapInfo/getPlotInfo"

    payload = {
        "gisCode": "14600766124649",
        "plotNo": "30",
    }

    try:
        response = requests.post(url, json=payload, timeout=30)

        print("Status code:", response.status_code)
        print("Response text:")
        print(response.text)

    except requests.exceptions.RequestException as exc:
        print("Request failed:", exc)


if __name__ == "__main__":
    run_bhunaksha_plot_info_demo()
