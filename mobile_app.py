"""
mobile_app.py — Мобильное приложение на Kivy.
Подключается к серверу (server.py) запущенному на ноутбуке.
Показывает итоги как в Админ Панели.

Сборка в APK:
    pip install buildozer
    buildozer init      # создаст buildozer.spec
    buildozer android debug

Зависимости Kivy: kivy, requests, android (для биометрии — через pyjnius)
"""

import os
import json
import threading
import requests
from datetime import date, timedelta

# ── Kivy настройки до импорта ──────────────────────────────────────────────
os.environ.setdefault("KIVY_NO_ENV_CONFIG", "1")

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.togglebutton import ToggleButton
from kivy.clock import Clock, mainthread
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Rectangle

# ── Цвета ──────────────────────────────────────────────────────────────────
C = {
    "bg":        "#0F172A",   # тёмный фон
    "card":      "#1E293B",   # карточки
    "card2":     "#334155",   # вторичные карточки
    "accent":    "#3B82F6",   # синий акцент
    "green":     "#22C55E",
    "red":       "#EF4444",
    "gold":      "#F59E0B",
    "text":      "#F1F5F9",
    "muted":     "#94A3B8",
    "border":    "#475569",
}

# ── Настройки подключения (хранятся локально) ──────────────────────────────
SETTINGS_FILE = "mobile_settings.json"
DEFAULT_SERVER = "http://192.168.1.100:5050"  # заменить на IP ноутбука


def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"server_url": DEFAULT_SERVER, "token": None, "biometry_type": "none"}


def save_settings(s: dict):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(s, f)


# ══════════════════════════════════════════════════════════════════════════════
# API КЛИЕНТ
# ══════════════════════════════════════════════════════════════════════════════

class API:
    def __init__(self):
        self.settings = load_settings()

    @property
    def base(self) -> str:
        return self.settings.get("server_url", DEFAULT_SERVER).rstrip("/")

    @property
    def token(self) -> str | None:
        return self.settings.get("token")

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _post(self, path: str, body: dict, timeout=8) -> dict:
        try:
            r = requests.post(f"{self.base}{path}", json=body,
                              headers=self._headers(), timeout=timeout)
            return r.json()
        except requests.exceptions.ConnectionError:
            return {"ok": False, "error": "Нет соединения с сервером"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _get(self, path: str, params=None, timeout=8) -> dict:
        try:
            r = requests.get(f"{self.base}{path}", params=params,
                             headers=self._headers(), timeout=timeout)
            return r.json()
        except requests.exceptions.ConnectionError:
            return {"ok": False, "error": "Нет соединения с сервером"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def ping(self) -> dict:
        return self._get("/api/ping", timeout=4)

    def login_pin(self, pin: str) -> dict:
        return self._post("/api/auth/pin", {"pin": pin})

    def login_admin(self, password: str) -> dict:
        return self._post("/api/auth/admin_password", {"password": password})

    def login_biometry(self) -> dict:
        return self._post("/api/auth/biometry_login", {"confirmed": True})

    def get_biometry_config(self) -> dict:
        return self._get("/api/auth/biometry_config")

    def setup_pin(self, pin: str) -> dict:
        return self._post("/api/auth/setup_pin", {"pin": pin})

    def setup_biometry(self, enabled: bool, btype: str) -> dict:
        return self._post("/api/auth/setup_biometry",
                          {"enabled": enabled, "type": btype})

    def get_summary(self, date_from: str, date_to: str) -> dict:
        return self._get("/api/summary", {"from": date_from, "to": date_to})

    def get_summary_today(self) -> dict:
        return self._get("/api/summary/today")

    def save_token(self, token: str):
        self.settings["token"] = token
        save_settings(self.settings)

    def save_server_url(self, url: str):
        self.settings["server_url"] = url
        save_settings(self.settings)

    def logout(self):
        self.settings["token"] = None
        save_settings(self.settings)


api = API()


# ══════════════════════════════════════════════════════════════════════════════
# UI УТИЛИТЫ
# ══════════════════════════════════════════════════════════════════════════════

def hex2rgba(h: str):
    return get_color_from_hex(h)


def make_label(text="", size=14, bold=False, color=None, halign="left", **kw):
    lbl = Label(
        text=text,
        font_size=dp(size),
        bold=bold,
        color=hex2rgba(color or C["text"]),
        halign=halign,
        text_size=(None, None),
        **kw
    )
    lbl.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
    return lbl


def make_button(text, bg=None, color="#FFFFFF", on_press=None, height=48, **kw):
    btn = Button(
        text=text,
        font_size=dp(15),
        bold=True,
        color=hex2rgba(color),
        background_normal="",
        background_color=hex2rgba(bg or C["accent"]),
        size_hint_y=None,
        height=dp(height),
        **kw
    )
    if on_press:
        btn.bind(on_press=on_press)
    return btn


def make_input(hint="", password=False, **kw):
    ti = TextInput(
        hint_text=hint,
        password=password,
        multiline=False,
        font_size=dp(16),
        background_color=hex2rgba(C["card2"]),
        foreground_color=hex2rgba(C["text"]),
        hint_text_color=hex2rgba(C["muted"]),
        cursor_color=hex2rgba(C["accent"]),
        size_hint_y=None,
        height=dp(48),
        padding=[dp(12), dp(12)],
        **kw
    )
    return ti


def show_toast(msg: str, duration=2.5):
    """Маленький popup-уведомление снизу экрана."""
    lbl = Label(text=msg, font_size=dp(14), color=hex2rgba(C["text"]))
    popup = Popup(title="", content=lbl, size_hint=(0.75, None),
                  height=dp(60), separator_height=0,
                  background_color=hex2rgba(C["card"]))
    popup.open()
    Clock.schedule_once(lambda dt: popup.dismiss(), duration)


class CardBox(BoxLayout):
    """Карточка с закруглёнными углами и тёмным фоном."""
    def __init__(self, bg=None, radius=12, padding=12, **kw):
        super().__init__(padding=dp(padding), **kw)
        self._bg_color = hex2rgba(bg or C["card"])
        self._radius = dp(radius)
        with self.canvas.before:
            self._col = Color(*self._bg_color)
            self._rect = RoundedRectangle(size=self.size, pos=self.pos,
                                          radius=[self._radius])
        self.bind(size=self._upd, pos=self._upd)

    def _upd(self, *_):
        self._rect.size = self.size
        self._rect.pos = self.pos


# ══════════════════════════════════════════════════════════════════════════════
# ЭКРАНЫ
# ══════════════════════════════════════════════════════════════════════════════

class LoginScreen(Screen):
    """Экран входа — пин / биометрия / пароль админа."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._build()

    def _build(self):
        with self.canvas.before:
            Color(*hex2rgba(C["bg"]))
            self._bg = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=lambda w, s: setattr(self._bg, "size", s),
                  pos=lambda w, p: setattr(self._bg, "pos", p))

        root = BoxLayout(orientation="vertical", padding=dp(30), spacing=dp(16))

        # Заголовок
        root.add_widget(Label(size_hint_y=None, height=dp(20)))
        root.add_widget(make_label("📦 Карго Админ", size=26, bold=True,
                                   color=C["accent"], halign="center"))
        root.add_widget(make_label("Панель управления", size=14,
                                   color=C["muted"], halign="center"))
        root.add_widget(Label(size_hint_y=None, height=dp(10)))

        # Карточка входа
        card = CardBox(orientation="vertical", spacing=dp(12),
                       size_hint_y=None, height=dp(360))

        card.add_widget(make_label("🔐 Введите пин-код", size=16, bold=True,
                                   color=C["text"], halign="center"))

        # PIN поле
        self.pin_input = make_input(hint="• • • • ", password=True,
                                    input_filter="int")
        card.add_widget(self.pin_input)

        # Кнопка входа по пин
        card.add_widget(make_button("Войти", bg=C["accent"],
                                    on_press=self._login_pin))

        # Разделитель
        card.add_widget(make_label("─── или ───", size=12,
                                   color=C["muted"], halign="center"))

        # Кнопка биометрии
        self.bio_btn = make_button("👆 Биометрия", bg=C["card2"],
                                   on_press=self._login_bio)
        card.add_widget(self.bio_btn)

        # Кнопка через пароль админа
        card.add_widget(make_button("🔑 Забыл пин — войти через пароль",
                                    bg=C["card2"], height=44,
                                    on_press=self._show_admin_pwd))

        # Статус
        self.status_lbl = make_label("", size=13, color=C["red"],
                                     halign="center")
        card.add_widget(self.status_lbl)

        root.add_widget(card)

        # Кнопка настроек сервера
        root.add_widget(make_button("⚙️ Сервер", bg=C["card2"], height=36,
                                    on_press=self._show_server_settings))

        root.add_widget(Label())  # spacer
        self.add_widget(root)

    def on_enter(self):
        """Обновить состояние кнопки биометрии при входе на экран."""
        def _check(dt):
            cfg = api.get_biometry_config()
            bio_on = cfg.get("biometry_enabled", False)
            btype  = cfg.get("biometry_type", "none")
            if bio_on and btype != "none":
                icon = "👆" if btype == "fingerprint" else "🙂"
                self.bio_btn.text = f"{icon} Войти биометрией"
                self.bio_btn.background_color = hex2rgba(C["green"])
            else:
                self.bio_btn.text = "👆 Биометрия (не настроена)"
                self.bio_btn.background_color = hex2rgba(C["card2"])
        threading.Thread(target=_check, args=(0,), daemon=True).start()

    def _set_status(self, msg, color=None):
        self.status_lbl.text = msg
        self.status_lbl.color = hex2rgba(color or C["red"])

    def _login_pin(self, *_):
        pin = self.pin_input.text.strip()
        if not pin:
            self._set_status("Введите пин-код")
            return
        self._set_status("⏳ Проверяем...", C["muted"])

        def _do():
            res = api.login_pin(pin)
            self._handle_login_result(res)

        threading.Thread(target=_do, daemon=True).start()

    def _login_bio(self, *_):
        """Биометрия: запрашиваем Android BiometricPrompt через pyjnius."""
        try:
            from jnius import autoclass  # доступно только в APK
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Executor        = autoclass("java.util.concurrent.Executors")
            BiometricPrompt = autoclass("androidx.biometric.BiometricPrompt")
            PromptInfo      = autoclass("androidx.biometric.BiometricPrompt$PromptInfo")
            AuthCallback    = autoclass("androidx.biometric.BiometricPrompt$AuthenticationCallback")

            activity = PythonActivity.mActivity
            executor = Executor.newSingleThreadExecutor()

            class _CB(AuthCallback):
                def onAuthenticationSucceeded(self, result):
                    Clock.schedule_once(lambda dt: _on_bio_success())

                def onAuthenticationFailed(self):
                    Clock.schedule_once(lambda dt: self._set_status("Биометрия не распознана"))

                def onAuthenticationError(self, code, msg):
                    Clock.schedule_once(lambda dt: self._set_status(f"Ошибка: {msg}"))

            cb = _CB()
            prompt = BiometricPrompt(activity, executor, cb)
            info = (PromptInfo.Builder()
                    .setTitle("Вход в Карго Админ")
                    .setSubtitle("Используйте биометрию для входа")
                    .setNegativeButtonText("Отмена")
                    .build())
            prompt.authenticate(info)

            def _on_bio_success():
                self._set_status("✅ Биометрия подтверждена", C["green"])
                def _do():
                    res = api.login_biometry()
                    self._handle_login_result(res)
                threading.Thread(target=_do, daemon=True).start()

        except ImportError:
            # Не APK — симулируем (для тестирования на ПК)
            show_toast("Биометрия доступна только в APK")

    def _show_admin_pwd(self, *_):
        """Popup для входа через пароль администратора."""
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        content.add_widget(make_label("Пароль администратора", size=15, bold=True,
                                      halign="center"))
        pwd_inp = make_input(hint="Пароль", password=True)
        content.add_widget(pwd_inp)
        status = make_label("", size=13, color=C["red"], halign="center")
        content.add_widget(status)

        def _do_login(*_):
            pwd = pwd_inp.text.strip()
            if not pwd:
                status.text = "Введите пароль"
                return
            status.text = "⏳..."
            status.color = hex2rgba(C["muted"])

            def _req():
                res = api.login_admin(pwd)
                Clock.schedule_once(lambda dt: _after(res))

            def _after(res):
                if res.get("ok"):
                    popup.dismiss()
                    api.save_token(res["token"])
                    self._go_dashboard()
                else:
                    status.text = res.get("error", "Ошибка")
                    status.color = hex2rgba(C["red"])

            threading.Thread(target=_req, daemon=True).start()

        content.add_widget(make_button("Войти", on_press=_do_login))

        popup = Popup(title="Вход через пароль", content=content,
                      size_hint=(0.85, None), height=dp(280),
                      background_color=hex2rgba(C["card"]))
        popup.open()

    def _show_server_settings(self, *_):
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        content.add_widget(make_label("IP адрес сервера (ноутбука)", size=14))
        url_inp = make_input(hint="http://192.168.x.x:5050")
        url_inp.text = api.settings.get("server_url", DEFAULT_SERVER)
        content.add_widget(url_inp)
        status = make_label("", size=13, color=C["muted"], halign="center")
        content.add_widget(status)

        def _save(*_):
            url = url_inp.text.strip().rstrip("/")
            if not url:
                return
            api.save_server_url(url)
            status.text = "⏳ Проверяем соединение..."

            def _ping():
                res = api.ping()
                Clock.schedule_once(
                    lambda dt: setattr(status, "text",
                                       "✅ Сервер доступен!" if res.get("ok")
                                       else f"❌ {res.get('error', 'Недоступен')}")
                )
                if res.get("ok"):
                    status.color = hex2rgba(C["green"])
                else:
                    status.color = hex2rgba(C["red"])

            threading.Thread(target=_ping, daemon=True).start()

        content.add_widget(make_button("Сохранить и проверить", on_press=_save))

        popup = Popup(title="Настройки сервера", content=content,
                      size_hint=(0.9, None), height=dp(280),
                      background_color=hex2rgba(C["card"]))
        popup.open()

    @mainthread
    def _handle_login_result(self, res):
        if res.get("ok"):
            api.save_token(res["token"])
            self.pin_input.text = ""
            self._go_dashboard()
        else:
            self._set_status(res.get("error", "Ошибка входа"))
            self.pin_input.text = ""

    def _go_dashboard(self):
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "dashboard"


# ─────────────────────────────────────────────────────────────────────────────

class DashboardScreen(Screen):
    """Главный экран — итоги как в Админ Панели."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._build()

    def _build(self):
        with self.canvas.before:
            Color(*hex2rgba(C["bg"]))
            self._bg = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=lambda w, s: setattr(self._bg, "size", s),
                  pos=lambda w, p: setattr(self._bg, "pos", p))

        root = BoxLayout(orientation="vertical", padding=[dp(12), dp(10)],
                         spacing=dp(8))

        # ── Шапка ──
        header = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        header.add_widget(make_label("📊 Итоги", size=20, bold=True,
                                     color=C["accent"]))
        self.refresh_btn = make_button("↻", bg=C["card2"], width=dp(44),
                                       size_hint_x=None,
                                       on_press=lambda *_: self._load())
        header.add_widget(self.refresh_btn)
        settings_btn = make_button("⚙", bg=C["card2"], width=dp(44),
                                   size_hint_x=None,
                                   on_press=lambda *_: self._go_settings())
        header.add_widget(settings_btn)
        root.add_widget(header)

        # ── Выбор периода ──
        period_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
        self.period_spinner = Spinner(
            text="Сегодня",
            values=["Сегодня", "Вчера", "Эта неделя", "Этот месяц"],
            size_hint_x=0.6,
            font_size=dp(14),
            background_color=hex2rgba(C["card2"]),
            color=hex2rgba(C["text"]),
        )
        self.period_spinner.bind(text=lambda *_: self._load())
        period_row.add_widget(self.period_spinner)
        period_row.add_widget(make_button("Обновить", bg=C["accent"],
                                          on_press=lambda *_: self._load()))
        root.add_widget(period_row)

        # ── Статус загрузки ──
        self.status_lbl = make_label("", size=13, color=C["muted"],
                                     halign="center")
        root.add_widget(self.status_lbl)

        # ── Прокручиваемое содержимое ──
        scroll = ScrollView()
        self.content = BoxLayout(orientation="vertical", spacing=dp(10),
                                 size_hint_y=None, padding=[0, dp(4)])
        self.content.bind(minimum_height=self.content.setter("height"))
        scroll.add_widget(self.content)
        root.add_widget(scroll)

        # ── Выход ──
        root.add_widget(make_button("🚪 Выйти", bg=C["card2"], height=40,
                                    on_press=self._logout))

        self.add_widget(root)

    def on_enter(self):
        self._load()

    def _load(self, *_):
        self.status_lbl.text = "⏳ Загружаем данные..."
        period = self.period_spinner.text
        today = date.today()

        if period == "Сегодня":
            d_from = d_to = today
        elif period == "Вчера":
            d_from = d_to = today - timedelta(days=1)
        elif period == "Эта неделя":
            d_from = today - timedelta(days=today.weekday())
            d_to = today
        else:  # Этот месяц
            d_from = today.replace(day=1)
            d_to = today

        def _do():
            res = api.get_summary(
                d_from.strftime("%Y-%m-%d"),
                d_to.strftime("%Y-%m-%d")
            )
            Clock.schedule_once(lambda dt: self._render(res))

        threading.Thread(target=_do, daemon=True).start()

    @mainthread
    def _render(self, data: dict):
        self.content.clear_widgets()

        if not data.get("ok"):
            err = data.get("error", "Неизвестная ошибка")
            if "токен" in err.lower() or "недействителен" in err.lower():
                self._logout()
                return
            self.status_lbl.text = f"❌ {err}"
            return

        self.status_lbl.text = (
            f"📅 {data['period']['from']}  →  {data['period']['to']}"
        )

        # ── Карточки доходов по типу оплаты ──
        self.content.add_widget(
            make_label("  💳 По типу оплаты", size=13, bold=True,
                       color=C["muted"])
        )

        pay_grid = GridLayout(cols=3, spacing=dp(8),
                              size_hint_y=None, height=dp(100))
        pay_grid.add_widget(self._pay_card("Alif", data["alif"], C["accent"]))
        pay_grid.add_widget(self._pay_card("DC",   data["dc"],   C["gold"]))
        pay_grid.add_widget(self._pay_card("$",    data["cash"], C["green"]))
        self.content.add_widget(pay_grid)

        # ── Итоговые карточки ──
        self.content.add_widget(
            make_label("  📈 Итоги", size=13, bold=True, color=C["muted"])
        )
        summary_items = [
            ("💰 Общий доход",      f"{data['total_income']:.2f} сом", C["green"]),
            ("📉 Расходы склада",   f"{data['warehouse_expenses']:.2f} сом", C["red"]),
            ("👷 Расходы работников", f"{data['employee_expenses']:.2f} сом", C["red"]),
            ("📊 Чистая прибыль",   f"{data['net_profit']:.2f} сом",
             C["green"] if data["net_profit"] >= 0 else C["red"]),
        ]
        for label, value, color in summary_items:
            self.content.add_widget(self._summary_row(label, value, color))

        # ── Статистика ──
        self.content.add_widget(
            make_label("  📦 Статистика", size=13, bold=True, color=C["muted"])
        )
        stat_items = [
            ("🧾 Заказов",       str(data["order_count"]),            C["text"]),
            ("⚖️ Всего кг",      f"{data['total_kg']:.2f} кг",       C["text"]),
            ("✈️ Авиа кг",       f"{data['total_air_kg']:.2f} кг",   C["text"]),
            ("📐 Кубов",         f"{data['total_m3']:.3f} м³",       C["text"]),
        ]
        for label, value, color in stat_items:
            self.content.add_widget(self._summary_row(label, value, color))

        self.content.add_widget(Label(size_hint_y=None, height=dp(20)))

    def _pay_card(self, title: str, amount: float, color: str):
        card = CardBox(orientation="vertical", bg=C["card"],
                       size_hint_y=None, height=dp(90), padding=dp(8))
        card.add_widget(make_label(title, size=15, bold=True,
                                   color=color, halign="center"))
        card.add_widget(make_label(f"{amount:.2f}", size=16, bold=True,
                                   color=C["text"], halign="center"))
        card.add_widget(make_label("сомони", size=11, color=C["muted"],
                                   halign="center"))
        return card

    def _summary_row(self, label: str, value: str, color: str):
        row = CardBox(orientation="horizontal", bg=C["card"],
                      size_hint_y=None, height=dp(52), padding=[dp(14), dp(8)],
                      spacing=dp(8))
        row.add_widget(make_label(label, size=14, color=C["text"]))
        row.add_widget(make_label(value, size=15, bold=True,
                                  color=color, halign="right"))
        return row

    def _logout(self, *_):
        api.logout()
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "login"

    def _go_settings(self):
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "settings"


# ─────────────────────────────────────────────────────────────────────────────

class SettingsScreen(Screen):
    """Экран настроек — пин, биометрия."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._build()

    def _build(self):
        with self.canvas.before:
            Color(*hex2rgba(C["bg"]))
            self._bg = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=lambda w, s: setattr(self._bg, "size", s),
                  pos=lambda w, p: setattr(self._bg, "pos", p))

        root = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(14))
        root.add_widget(make_label("⚙️ Настройки", size=20, bold=True,
                                   color=C["accent"]))

        # ── Сменить пин ──
        pin_card = CardBox(orientation="vertical", spacing=dp(10),
                           size_hint_y=None, height=dp(180))
        pin_card.add_widget(make_label("🔒 Изменить пин-код", size=15, bold=True))
        self.new_pin1 = make_input(hint="Новый пин (мин. 4 цифры)", password=True,
                                   input_filter="int")
        self.new_pin2 = make_input(hint="Повторите пин", password=True,
                                   input_filter="int")
        pin_card.add_widget(self.new_pin1)
        pin_card.add_widget(self.new_pin2)
        self.pin_status = make_label("", size=13, color=C["red"])
        pin_card.add_widget(self.pin_status)
        pin_card.add_widget(make_button("Сохранить пин", on_press=self._save_pin))
        root.add_widget(pin_card)

        # ── Биометрия ──
        bio_card = CardBox(orientation="vertical", spacing=dp(10),
                           size_hint_y=None, height=dp(180))
        bio_card.add_widget(make_label("👆 Биометрия", size=15, bold=True))

        self.bio_type = Spinner(
            text="Отпечаток пальца",
            values=["Отпечаток пальца", "Распознавание лица"],
            font_size=dp(14),
            background_color=hex2rgba(C["card2"]),
            color=hex2rgba(C["text"]),
            size_hint_y=None, height=dp(44),
        )
        bio_card.add_widget(self.bio_type)

        btn_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        btn_row.add_widget(make_button("✅ Включить", bg=C["green"],
                                       on_press=lambda *_: self._set_bio(True)))
        btn_row.add_widget(make_button("❌ Выключить", bg=C["red"],
                                       on_press=lambda *_: self._set_bio(False)))
        bio_card.add_widget(btn_row)
        self.bio_status = make_label("", size=13, color=C["muted"])
        bio_card.add_widget(self.bio_status)
        root.add_widget(bio_card)

        root.add_widget(Label())  # spacer
        root.add_widget(make_button("← Назад", bg=C["card2"],
                                    on_press=self._back))
        self.add_widget(root)

    def on_enter(self):
        def _check(dt):
            cfg = api.get_biometry_config()
            bio_on = cfg.get("biometry_enabled", False)
            btype  = cfg.get("biometry_type", "none")
            icon = "✅ Включена" if bio_on else "❌ Выключена"
            t = "отпечаток" if btype == "fingerprint" else ("лицо" if btype == "face" else "—")
            Clock.schedule_once(lambda dt2: setattr(
                self.bio_status, "text",
                f"Статус: {icon}  |  Тип: {t}"
            ))
        threading.Thread(target=_check, args=(0,), daemon=True).start()

    def _save_pin(self, *_):
        p1 = self.new_pin1.text.strip()
        p2 = self.new_pin2.text.strip()
        if len(p1) < 4:
            self.pin_status.text = "Пин минимум 4 цифры"
            return
        if p1 != p2:
            self.pin_status.text = "Пин-коды не совпадают"
            return
        self.pin_status.text = "⏳..."
        self.pin_status.color = hex2rgba(C["muted"])

        def _do():
            res = api.setup_pin(p1)
            @mainthread
            def _after():
                if res.get("ok"):
                    self.pin_status.text = "✅ Пин сохранён"
                    self.pin_status.color = hex2rgba(C["green"])
                    self.new_pin1.text = ""
                    self.new_pin2.text = ""
                else:
                    self.pin_status.text = res.get("error", "Ошибка")
                    self.pin_status.color = hex2rgba(C["red"])
            _after()

        threading.Thread(target=_do, daemon=True).start()

    def _set_bio(self, enable: bool):
        btype_text = self.bio_type.text
        btype = "fingerprint" if "палец" in btype_text.lower() else "face"
        self.bio_status.text = "⏳..."

        def _do():
            res = api.setup_biometry(enable, btype if enable else "none")
            @mainthread
            def _after():
                if res.get("ok"):
                    status = "✅ Включена" if enable else "❌ Выключена"
                    self.bio_status.text = f"Статус: {status}"
                    self.bio_status.color = hex2rgba(C["green"] if enable else C["muted"])
                else:
                    self.bio_status.text = res.get("error", "Ошибка")
                    self.bio_status.color = hex2rgba(C["red"])
            _after()

        threading.Thread(target=_do, daemon=True).start()

    def _back(self, *_):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "dashboard"


# ══════════════════════════════════════════════════════════════════════════════
# ПРИЛОЖЕНИЕ
# ══════════════════════════════════════════════════════════════════════════════

class CargoAdminApp(App):
    def build(self):
        Window.clearcolor = hex2rgba(C["bg"])

        sm = ScreenManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(DashboardScreen(name="dashboard"))
        sm.add_widget(SettingsScreen(name="settings"))
        return sm


if __name__ == "__main__":
    CargoAdminApp().run()
