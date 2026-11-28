from evalscope.service import run_service

if __name__ == "__main__":
    run_service(
        host="127.0.0.1",
        port=9000,
        debug=True,
        outputs="./outputs"
    )

