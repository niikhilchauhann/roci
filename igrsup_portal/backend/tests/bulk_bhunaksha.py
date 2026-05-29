from app.services.bhunaksha_demo_service import BhunakshaDemoService


if __name__ == "__main__":
    service = BhunakshaDemoService()
    summary = service.run(
        district="Ayodhya",
        tehsil="Sadar",
        village="Demo Village",
        plot_start=1,
        plot_end=10,
    )

    print("Bhunaksha bulk demo complete")
    for key, value in summary.items():
        print(f"{key}: {value}")
