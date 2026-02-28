import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from collector import collect_snapshot
from db import get_conn, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    asyncio.create_task(background_loop())
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


async def background_loop():
    while True:
        try:
            collect_snapshot()
        except Exception as e:
            print("Collector error:", e)
        await asyncio.sleep(3600 - (time.time() % 3600))


@app.get("/", response_class=HTMLResponse)
def dashboard():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT timestamp, total_xp
        FROM snapshots
        ORDER BY timestamp
    """)
    rows = cur.fetchall()

    timestamps = [r["timestamp"] for r in rows]
    xp = [r["total_xp"] for r in rows]

    conn.close()

    return f"""
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <h1>RS3 Tracker</h1>
        <canvas id="xpChart"></canvas>
        <script>
            new Chart(document.getElementById('xpChart'), {{
                type: 'line',
                data: {{
                    labels: {timestamps},
                    datasets: [{{
                        label: 'Total XP',
                        data: {xp}
                    }}]
                }}
            }});
        </script>
    </body>
    </html>
    """


@app.get("/update")
def manual_update():
    try:
        collect_snapshot()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
