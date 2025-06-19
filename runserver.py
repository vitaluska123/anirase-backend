import os
import uvicorn

if __name__ == "__main__":
    os.environ["DJANGO_SETTINGS_MODULE"] = "backend_v2.settings"
    uvicorn.run("backend_v2.asgi:application", host="127.0.0.1", port=8034, factory=False, reload=False)
