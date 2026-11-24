#!/usr/bin/env python3
"""
Options Scenario Calculator (Desktop GUI) with Real-Time Schwab Market Data
Matches the wireframe specification and Black-Scholes pricing logic.
Includes Ticker symbol entry, live Schwab quotes, option chain lookup,
interactive calendar picker, and quick expiration buttons.
"""

import sys
import math
import calendar
import datetime
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

# Ensure Python directory is on path
PYTHON_DIR = Path(__file__).resolve().parent
if str(PYTHON_DIR) not in sys.path:
    sys.path.append(str(PYTHON_DIR))

from schwab_data_service import fetch_schwab_setup


# --- Mathematical Engine ---
def normal_cdf(x):
    """Cumulative distribution function for standard normal distribution using math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def calculate_option_price(S, K, DTE, r, iv, option_type="call", logger: Any = None):
    """
    S: Stock Price
    K: Strike Price
    DTE: Days to Expiration
    r: Risk-free rate (e.g. 0.053 for 5.3%)
    iv: Implied Volatility (e.g. 0.35 for 35%)
    option_type: 'call' or 'put'
    """
    if S <= 0 or K <= 0 or iv <= 0:
        return 0.0
    
    if logger:
        logger.debug(f"Calculating option price: S={S}, K={K}, DTE={DTE}, r={r}, iv={iv}, type={option_type}")
        
    T = max(DTE / 365.0, 0.00001)
    sigma_sqrt_t = iv * math.sqrt(T)
    
    d1 = (math.log(S / K) + (r + 0.5 * (iv ** 2)) * T) / sigma_sqrt_t
    d2 = d1 - sigma_sqrt_t
    
    if option_type.lower() == "call":
        price = S * normal_cdf(d1) - K * math.exp(-r * T) * normal_cdf(d2)
    else:
        price = K * math.exp(-r * T) * normal_cdf(-d2) - S * normal_cdf(-d1)
        
    return max(0.0, price)


class CalendarPopup(tk.Toplevel):
    """A clean, lightweight calendar picker dialog using standard Tkinter."""
    def __init__(self, parent, initial_date, on_select):
        super().__init__(parent)
        self.title("Select Expiration Date")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.on_select = on_select
        self.current_year = initial_date.year
        self.current_month = initial_date.month
        self.selected_date = initial_date

        self.configure(bg="#ffffff", padx=12, pady=12)
        
        # Position near parent
        x = parent.winfo_rootx() + 50
        y = parent.winfo_rooty() + 80
        self.geometry(f"+{x}+{y}")
        
        self._build_header()
        self._build_grid()

    def _build_header(self):
        self.header_frame = tk.Frame(self, bg="#ffffff")
        self.header_frame.pack(fill="x", pady=(0, 8))

        btn_prev = tk.Button(self.header_frame, text="◀", font=("Segoe UI", 9), relief="flat",
                             bg="#f1f5f9", activebackground="#e2e8f0", command=self._prev_month)
        btn_prev.pack(side="left")

        self.lbl_month_year = tk.Label(self.header_frame, text="", font=("Segoe UI", 10, "bold"), bg="#ffffff", fg="#0f172a")
        self.lbl_month_year.pack(side="left", expand=True)

        btn_next = tk.Button(self.header_frame, text="▶", font=("Segoe UI", 9), relief="flat",
                             bg="#f1f5f9", activebackground="#e2e8f0", command=self._next_month)
        btn_next.pack(side="right")

    def _build_grid(self):
        if hasattr(self, "grid_frame"):
            self.grid_frame.destroy()

        self.grid_frame = tk.Frame(self, bg="#ffffff")
        self.grid_frame.pack()

        # Month Year display
        month_name = calendar.month_name[self.current_month]
        self.lbl_month_year.config(text=f"{month_name} {self.current_year}")

        # Day name headers
        day_names = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        for col, dname in enumerate(day_names):
            lbl = tk.Label(self.grid_frame, text=dname, font=("Segoe UI", 8, "bold"), 
                           bg="#ffffff", fg="#64748b", width=4, pady=2)
            lbl.grid(row=0, column=col)

        # Calendar matrix
        month_cal = calendar.monthcalendar(self.current_year, self.current_month)
        today = datetime.date.today()

        for row_idx, week in enumerate(month_cal, start=1):
            for col_idx, day in enumerate(week):
                if day == 0:
                    lbl_empty = tk.Label(self.grid_frame, text="", bg="#ffffff", width=4)
                    lbl_empty.grid(row=row_idx, column=col_idx)
                else:
                    d_obj = datetime.date(self.current_year, self.current_month, day)
                    is_today = (d_obj == today)
                    is_selected = (d_obj == self.selected_date)

                    bg = "#2563eb" if is_selected else ("#eff6ff" if is_today else "#ffffff")
                    fg = "#ffffff" if is_selected else ("#1d4ed8" if is_today else "#0f172a")

                    btn = tk.Button(self.grid_frame, text=str(day), width=3, relief="flat",
                                    font=("Consolas", 9, "bold" if (is_today or is_selected) else "normal"),
                                    bg=bg, fg=fg, activebackground="#93c5fd",
                                    command=lambda d=d_obj: self._select_date(d))
                    btn.grid(row=row_idx, column=col_idx, padx=1, pady=1)

    def _prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self._build_grid()

    def _next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self._build_grid()

    def _select_date(self, date_obj):
        self.on_select(date_obj)
        self.destroy()


class OptionsCalculatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Options Scenario Calculator - Schwab Real-Time")
        self.geometry("860x600")
        self.minsize(800, 520)
        self.configure(bg="#f8fafc")

        # Variables
        self.var_ticker = tk.StringVar(value="QQQ")
        self.last_loaded_ticker = ""
        self.option_type = tk.StringVar(value="call")
        
        today = datetime.date.today()
        default_exp = today + datetime.timedelta(days=14)
        
        self.var_exp_date = tk.StringVar(value=default_exp.strftime("%Y-%m-%d"))
        self.var_underlying = tk.StringVar(value="707.30")
        self.var_strike = tk.StringVar(value="707.00")
        self.var_iv = tk.StringVar(value="17.1")
        self.var_days_to_hold = tk.StringVar(value="21")
        self.var_anticipated_iv = tk.StringVar(value="17.1")
        self.var_anticipated_change = tk.StringVar(value="5.0")
        self.var_risk_free = tk.StringVar(value="5.3")
        self.var_status = tk.StringVar(value="Ready. Enter symbol to load live quote.")

        # Output Variables
        self.out_price_buy = tk.StringVar(value="$0.00")
        self.out_date_sell = tk.StringVar(value="--")
        self.out_price_sell = tk.StringVar(value="$0.00")
        self.out_underlying_sell = tk.StringVar(value="$0.00")
        self.out_pnl = tk.StringVar(value="+$0.00 (+0.0%)")
        self.out_dte_badge = tk.StringVar(value="14 DTE")
        
        self._build_ui()
        self.recalculate()

        # Auto-fetch QQQ data on launch
        self.after(200, self.fetch_schwab_data)

    def _build_ui(self):
        # Header
        header_frame = tk.Frame(self, bg="#f8fafc")
        header_frame.pack(fill="x", padx=30, pady=(16, 8))

        title_lbl = tk.Label(header_frame, text="Options Scenario Calculator", 
                             font=("Segoe UI", 18, "bold"), bg="#f8fafc", fg="#0f172a")
        title_lbl.pack(anchor="w")

        subtitle_lbl = tk.Label(header_frame, text="Simulate option exit prices and P&L with live Charles Schwab quotes & option chains.",
                                font=("Segoe UI", 9), bg="#f8fafc", fg="#64748b")
        subtitle_lbl.pack(anchor="w")

        # Main Layout: 2 Columns
        main_frame = tk.Frame(self, bg="#f8fafc")
        main_frame.pack(fill="both", expand=True, padx=30, pady=6)

        # Left Column: Inputs
        left_col = tk.Frame(main_frame, bg="#f8fafc", width=380)
        left_col.pack(side="left", fill="y", padx=(0, 25))

        # Right Column: Outputs Box
        right_col = tk.Frame(main_frame, bg="#f8fafc")
        right_col.pack(side="right", fill="both", expand=True)

        # 1. Ticker Symbol Box at the Top
        self._add_ticker_row(left_col)

        # Option Type Toggle
        type_frame = tk.Frame(left_col, bg="#f8fafc")
        type_frame.pack(fill="x", pady=4)
        tk.Label(type_frame, text="Option Type:", font=("Segoe UI", 9, "bold"), bg="#f8fafc", fg="#1e293b").pack(side="left")
        tk.Radiobutton(type_frame, text="Call", variable=self.option_type, value="call", 
                       command=self.recalculate, bg="#f8fafc", activebackground="#f8fafc").pack(side="left", padx=(15, 5))
        tk.Radiobutton(type_frame, text="Put", variable=self.option_type, value="put", 
                       command=self.recalculate, bg="#f8fafc", activebackground="#f8fafc").pack(side="left", padx=5)

        # Expiration Date with Calendar Button & Quick Buttons
        self._add_date_input_row(left_col)

        # Standard Input Rows (User can change freely, only updates output)
        self._add_input_row(left_col, "Underlying ($)", self.var_underlying)
        self._add_input_row(left_col, "Strike ($)", self.var_strike)
        self._add_input_row(left_col, "IV (%)", self.var_iv)
        self._add_input_row(left_col, "Days to hold", self.var_days_to_hold)
        self._add_input_row(left_col, "Anticipated IV @ sell (%)", self.var_anticipated_iv)
        self._add_input_row(left_col, "Anticipated Underlying change @ sell (%)", self.var_anticipated_change)

        # Output Card (Matches Wireframe Box)
        card = tk.Frame(right_col, bg="#eaedf1", highlightbackground="#2b333c", highlightthickness=2, padx=25, pady=25)
        card.pack(fill="both", expand=True, pady=6)

        # Price at Buy
        tk.Label(card, text="Price at Buy", font=("Segoe UI", 11, "bold"), bg="#eaedf1", fg="#212529").pack(anchor="w")
        self.lbl_price_buy = tk.Label(card, textvariable=self.out_price_buy, font=("Consolas", 18, "bold"), bg="#eaedf1", fg="#0f172a")
        self.lbl_price_buy.pack(anchor="w", pady=(2, 10))

        # Divider
        tk.Frame(card, bg="#cbd5e1", height=1).pack(fill="x", pady=5)

        # Date of Sell
        tk.Label(card, text="Date of Sell", font=("Segoe UI", 11, "bold"), bg="#eaedf1", fg="#212529").pack(anchor="w")
        self.lbl_date_sell = tk.Label(card, textvariable=self.out_date_sell, font=("Consolas", 16, "bold"), bg="#eaedf1", fg="#0f172a")
        self.lbl_date_sell.pack(anchor="w", pady=(2, 8))

        # Price at Sell
        tk.Label(card, text="Price at Sell", font=("Segoe UI", 11, "bold"), bg="#eaedf1", fg="#212529").pack(anchor="w")
        self.lbl_price_sell = tk.Label(card, textvariable=self.out_price_sell, font=("Consolas", 18, "bold"), bg="#eaedf1", fg="#0f172a")
        self.lbl_price_sell.pack(anchor="w", pady=(2, 10))

        # Divider
        tk.Frame(card, bg="#cbd5e1", height=1).pack(fill="x", pady=5)

        # Underlying Anticipated Price at Sell
        tk.Label(card, text="Underlying anticipated price at Sell", font=("Segoe UI", 11, "bold"), bg="#eaedf1", fg="#212529").pack(anchor="w")
        self.lbl_underlying_sell = tk.Label(card, textvariable=self.out_underlying_sell, font=("Consolas", 18, "bold"), bg="#eaedf1", fg="#0f172a")
        self.lbl_underlying_sell.pack(anchor="w", pady=(2, 12))

        # PnL Banner
        pnl_box = tk.Frame(card, bg="#ffffff", highlightbackground="#cbd5e1", highlightthickness=1, padx=15, pady=8)
        pnl_box.pack(fill="x", pady=6)

        tk.Label(pnl_box, text="ESTIMATED PROFIT / LOSS", font=("Segoe UI", 8, "bold"), bg="#ffffff", fg="#64748b").pack(anchor="w")
        self.lbl_pnl = tk.Label(pnl_box, textvariable=self.out_pnl, font=("Consolas", 14, "bold"), bg="#ffffff", fg="#16a34a")
        self.lbl_pnl.pack(anchor="w")

    def _add_ticker_row(self, parent):
        ticker_box = tk.Frame(parent, bg="#ffffff", highlightbackground="#2563eb", highlightthickness=1.5, padx=10, pady=8)
        ticker_box.pack(fill="x", pady=(0, 6))

        lbl = tk.Label(ticker_box, text="Ticker Symbol", font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#1e3a8a")
        lbl.pack(anchor="w")

        input_row = tk.Frame(ticker_box, bg="#ffffff")
        input_row.pack(fill="x", pady=(3, 3))

        self.entry_ticker = tk.Entry(input_row, textvariable=self.var_ticker, font=("Consolas", 12, "bold"),
                                     bg="#ffffff", fg="#0f172a", highlightthickness=1, highlightbackground="#94a3b8", relief="flat")
        self.entry_ticker.pack(side="left", fill="x", expand=True, ipady=3)
        self.entry_ticker.bind("<Return>", lambda e: self.fetch_schwab_data())

        self.btn_fetch = tk.Button(input_row, text="⚡ Load", font=("Segoe UI", 9, "bold"),
                                   bg="#2563eb", fg="#ffffff", activebackground="#1d4ed8", relief="flat", padx=10,
                                   command=self.fetch_schwab_data)
        self.btn_fetch.pack(side="right", padx=(6, 0))

        self.lbl_status = tk.Label(ticker_box, textvariable=self.var_status, font=("Segoe UI", 8),
                                   bg="#ffffff", fg="#64748b", wraplength=320, justify="left")
        self.lbl_status.pack(anchor="w")

    def _add_date_input_row(self, parent):
        row = tk.Frame(parent, bg="#f8fafc")
        row.pack(fill="x", pady=3)

        header = tk.Frame(row, bg="#f8fafc")
        header.pack(fill="x")

        lbl = tk.Label(header, text="Expiration Date", font=("Segoe UI", 8, "bold"), bg="#f8fafc", fg="#1e293b")
        lbl.pack(side="left")

        badge = tk.Label(header, textvariable=self.out_dte_badge, font=("Consolas", 8), bg="#e2e8f0", fg="#334155", padx=4)
        badge.pack(side="right")

        input_box = tk.Frame(row, bg="#f8fafc")
        input_box.pack(fill="x", pady=(2, 0))

        entry = tk.Entry(input_box, textvariable=self.var_exp_date, font=("Consolas", 10), bg="#ffffff", fg="#0f172a", 
                         highlightthickness=1, highlightbackground="#94a3b8", relief="flat")
        entry.pack(side="left", fill="x", expand=True, ipady=3)
        entry.bind("<KeyRelease>", lambda e: self.recalculate())

        btn_cal = tk.Button(input_box, text="📅 Pick", font=("Segoe UI", 8, "bold"), bg="#f1f5f9", 
                            relief="flat", highlightthickness=1, highlightbackground="#94a3b8",
                            command=self._open_calendar)
        btn_cal.pack(side="right", padx=(4, 0))

        # Quick day pills
        pill_frame = tk.Frame(row, bg="#f8fafc")
        pill_frame.pack(fill="x", pady=(2, 0))
        tk.Label(pill_frame, text="Quick:", font=("Segoe UI", 7), bg="#f8fafc", fg="#64748b").pack(side="left", padx=(0, 3))
        for days in [14, 30, 45, 60, 90]:
            btn = tk.Button(pill_frame, text=f"+{days}d", font=("Consolas", 7), relief="flat", bg="#f1f5f9",
                            command=lambda d=days: self._set_quick_exp(d))
            btn.pack(side="left", padx=1)

    def _open_calendar(self):
        try:
            curr = datetime.datetime.strptime(self.var_exp_date.get().strip(), "%Y-%m-%d").date()
        except ValueError:
            curr = datetime.date.today() + datetime.timedelta(days=7)

        CalendarPopup(self, curr, self._on_date_selected)

    def _on_date_selected(self, date_obj):
        self.var_exp_date.set(date_obj.strftime("%Y-%m-%d"))
        self.recalculate()

    def _set_quick_exp(self, days):
        target = datetime.date.today() + datetime.timedelta(days=days)
        self.var_exp_date.set(target.strftime("%Y-%m-%d"))
        self.recalculate()

    def _add_input_row(self, parent, label_text, var):
        row = tk.Frame(parent, bg="#f8fafc")
        row.pack(fill="x", pady=3)

        header = tk.Frame(row, bg="#f8fafc")
        header.pack(fill="x")

        lbl = tk.Label(header, text=label_text, font=("Segoe UI", 8, "bold"), bg="#f8fafc", fg="#1e293b")
        lbl.pack(side="left")

        entry = tk.Entry(row, textvariable=var, font=("Consolas", 10), bg="#ffffff", fg="#0f172a", 
                         highlightthickness=1, highlightbackground="#94a3b8", relief="flat")
        entry.pack(fill="x", ipady=3, pady=(2, 0))
        entry.bind("<KeyRelease>", lambda e: self.recalculate())

    def fetch_schwab_data(self):
        symbol = self.var_ticker.get().strip().upper()
        if not symbol:
            self.var_status.set("Please enter a ticker symbol.")
            self.lbl_status.configure(fg="#dc2626")
            return

        self.var_status.set(f"Fetching Schwab quote & option chain for {symbol}...")
        self.lbl_status.configure(fg="#2563eb")
        self.btn_fetch.configure(state="disabled")

        def _worker():
            try:
                data = fetch_schwab_setup(symbol=symbol, option_type=self.option_type.get())
                self.after(0, lambda: self._apply_schwab_data(data))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: self._apply_schwab_error(err_msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_schwab_data(self, data):
        self.btn_fetch.configure(state="normal")
        self.last_loaded_ticker = data["symbol"]

        # 1. Underlying price
        self.var_underlying.set(f"{data['underlying']:.2f}")

        # 2. Expiration Date (~14 DTE)
        self.var_exp_date.set(data["expirationDate"])

        # 3. Strike (ATM)
        self.var_strike.set(f"{data['strike']:.2f}")

        # 4. IV
        self.var_iv.set(f"{data['iv']:.1f}")
        self.var_anticipated_iv.set(f"{data['iv']:.1f}")

        # 5. Days to hold = 21 (7 days beyond expiration)
        days_to_hold = data.get("daysToHold", 21)
        self.var_days_to_hold.set(str(days_to_hold))

        self.var_status.set(f"✓ Loaded {data['symbol']}: ${data['underlying']:.2f} • Exp {data['expirationDate']} ({data['dte']}d) • ATM Strike ${data['strike']} • IV {data['iv']}%")
        self.lbl_status.configure(fg="#16a34a")

        self.recalculate()

    def _apply_schwab_error(self, err_msg):
        self.btn_fetch.configure(state="normal")
        self.var_status.set(f"Schwab API error: {err_msg}")
        self.lbl_status.configure(fg="#dc2626")

    def recalculate(self):
        try:
            underlying = float(self.var_underlying.get())
            strike = float(self.var_strike.get())
            iv = float(self.var_iv.get()) / 100.0
            days_to_hold = int(float(self.var_days_to_hold.get()))
            anticipated_iv = float(self.var_anticipated_iv.get()) / 100.0
            anticipated_change = float(self.var_anticipated_change.get()) / 100.0
            risk_free = float(self.var_risk_free.get()) / 100.0
            
            exp_date_str = self.var_exp_date.get().strip()
            exp_date = datetime.datetime.strptime(exp_date_str, "%Y-%m-%d").date()
            today = datetime.date.today()
            
            total_dte = (exp_date - today).days
            if total_dte >= 0:
                self.out_dte_badge.set(f"{total_dte} DTE")
            else:
                self.out_dte_badge.set(f"Expired ({total_dte}d)")

            # 1. Price at Buy
            buy_price = calculate_option_price(underlying, strike, max(total_dte, 0.0001), 
                                               risk_free, max(iv, 0.001), self.option_type.get())
            
            # 2. Date of Sell
            sell_date = today + datetime.timedelta(days=days_to_hold)
            sell_date_str = sell_date.strftime("%a, %b %d, %Y")

            # 3. Underlying at Sell
            underlying_sell = underlying * (1.0 + anticipated_change)

            # 4. Price at Sell
            remaining_dte = max(total_dte - days_to_hold, 0)
            if remaining_dte <= 0:
                if self.option_type.get() == "call":
                    sell_price = max(0.0, underlying_sell - strike)
                else:
                    sell_price = max(0.0, strike - underlying_sell)
            else:
                sell_price = calculate_option_price(underlying_sell, strike, remaining_dte, 
                                                    risk_free, max(anticipated_iv, 0.001), self.option_type.get())

            # 5. P&L
            profit_per_share = sell_price - buy_price
            profit_per_contract = profit_per_share * 100
            roi = (profit_per_share / buy_price * 100) if buy_price > 0 else 0.0

            # Set text
            self.out_price_buy.set(f"${buy_price:.2f}")
            self.out_date_sell.set(sell_date_str)
            self.out_price_sell.set(f"${sell_price:.2f}")
            self.out_underlying_sell.set(f"${underlying_sell:.2f}")

            sign = "+" if profit_per_contract >= 0 else ""
            pnl_color = "#16a34a" if profit_per_contract >= 0 else "#dc2626"
            self.out_pnl.set(f"{sign}${profit_per_contract:.2f} ({sign}{roi:.1f}%) [${profit_per_share:.2f}/sh]")
            self.lbl_pnl.configure(fg=pnl_color)

        except Exception:
            # Silently ignore during in-progress typing
            pass


if __name__ == "__main__":
    app = OptionsCalculatorApp()
    app.mainloop()
