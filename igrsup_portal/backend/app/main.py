import argparse
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.config import settings
from app.services.bhunaksha_demo_service import BhunakshaDemoService
from app.utils.logging import configure_logging, logger


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging(settings.log_level)
    logger.info("Starting {} in {}", settings.app_name, settings.app_env)
    yield
    logger.info("Stopping {}", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    logger.warning("Request validation failed: {}", exc)
    return JSONResponse(status_code=400, content={"status": "ERROR", "detail": str(exc)})


def run_bhunaksha_demo(
    district: str,
    tehsil: str,
    village: str,
    plot_start: int,
    plot_end: int,
) -> None:
    configure_logging(settings.log_level)
    service = BhunakshaDemoService()
    summary = service.run(
        district=district,
        tehsil=tehsil,
        village=village,
        plot_start=plot_start,
        plot_end=plot_end,
    )
    logger.info("Bhunaksha demo completed: {}", summary)
    print("\nBhunaksha Demo Summary")
    for key, value in summary.items():
        print(f"{key}: {value}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ROCI Ayodhya backend entry point")
    parser.add_argument("--demo", action="store_true", help="Run the Bhunaksha Ayodhya CSV demo scraper flow.")
    parser.add_argument("--district", default="Ayodhya", help="District name for the demo flow.")
    parser.add_argument("--tehsil", default="Sadar", help="Tehsil name for the demo flow.")
    parser.add_argument("--village", default="Demo Village", help="Village name for the demo flow.")
    parser.add_argument("--plot-start", type=int, default=1, help="Starting plot number.")
    parser.add_argument("--plot-end", type=int, default=10, help="Ending plot number.")
    return parser


if __name__ == "__main__":
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.demo:
        run_bhunaksha_demo(
            district=args.district,
            tehsil=args.tehsil,
            village=args.village,
            plot_start=args.plot_start,
            plot_end=args.plot_end,
        )
    else:
        print("FastAPI app entry point loaded. Run with uvicorn app.main:app --reload or use --demo for the Bhunaksha CSV flow.")
