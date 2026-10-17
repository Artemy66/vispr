import os
import sqlite3
import time
from functools import wraps

from flask import (
    Flask, request, redirect, session,
    render_template, Response, url_for, flash
)
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

DB_PATH = os.environ.get("DB_PATH", "/data/app.db")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")

#Метрики Prometheus
VISITS = Counter("site_visits_total", "Total visits", ["path"])
LEADS_TOTAL = Counter("site_leads_total", "Total leads submitted")
ADMIN_EDITS = Counter("site_admin_edits_total", "Total admin edits")
UPTIME = Gauge("site_uptime_seconds", "Uptime in seconds")

START_TIME = time.time()


#База данных
def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS content (
            k TEXT PRIMARY KEY,
            v TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            message TEXT,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    #значения по умолчанию
    defaults = {
        "title": "Моё приложение",
        "body": "Отредактируйте этот текст в админке.",
        "phone": "+7 (900) 000-00-00",
        "email": "hello@example.com",
    }
    for k, v in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO content(k, v) VALUES (?, ?)", (k, v)
        )
    conn.commit()
    conn.close()


def get_content():
    conn = get_db()
    rows = conn.execute("SELECT k, v FROM content").fetchall()
    conn.close()
    return {row["k"]: row["v"] for row in rows}


#Счётчик посещений
@app.before_request
def count_visit():
    #не считаем служебные эндпоинты
    if request.path in ("/metrics", "/health", "/favicon.ico"):
        return
    VISITS.labels(request.path).inc()
    UPTIME.set(time.time() - START_TIME)


#Публичная часть
@app.route("/")
def index():
    content = get_content()
    return render_template("index.html", content=content)


@app.route("/lead", methods=["POST"])
def lead():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    message = request.form.get("message", "").strip()

    if not name or not phone:
        flash("Имя и телефон обязательны", "error")
        return redirect(url_for("index"))

    conn = get_db()
    conn.execute(
        "INSERT INTO leads(name, phone, message) VALUES (?, ?, ?)",
        (name, phone, message),
    )
    conn.commit()
    conn.close()

    LEADS_TOTAL.inc()
    flash("Спасибо! Мы свяжемся с вами.", "success")
    return redirect(url_for("index"))


#Админка
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("admin"))
        error = "Неверный пароль"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    if request.method == "POST":
        conn = get_db()
        for key in ("title", "body", "phone", "email"):
            value = request.form.get(key, "")
            conn.execute(
                "INSERT INTO content(k, v) VALUES (?, ?) "
                "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                (key, value),
            )
        conn.commit()
        conn.close()
        ADMIN_EDITS.inc()
        flash("Сохранено", "success")
        return redirect(url_for("admin"))

    content = get_content()

    conn = get_db()
    leads = conn.execute(
        "SELECT id, name, phone, message, ts FROM leads ORDER BY id DESC LIMIT 100"
    ).fetchall()
    conn.close()

    return render_template("admin.html", content=content, leads=leads)


#Health и метрики
@app.route("/health")
def health():
    try:
        conn = get_db()
        conn.execute("SELECT 1")
        conn.close()
        return {"status": "ok", "uptime": round(time.time() - START_TIME, 1)}, 200
    except Exception as e:
        return {"status": "error", "detail": str(e)}, 500


@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


#Запуск
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8000)
else:
    #при запуске через gunicorn
    init_db()