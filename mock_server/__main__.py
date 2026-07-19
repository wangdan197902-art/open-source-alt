"""直接运行: python3 -m mock_server"""
import uvicorn


def main():
    uvicorn.run(
        "mock_server.main:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
