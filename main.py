import customtkinter as ctk
import threading
import time
import queue
from automation import InstagramBot

ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Instagram Auto Unlike Tool")
        self.geometry("900x650")

        self.bot = InstagramBot(log_callback=self.queue_log_message, stats_callback=self.queue_stats_update)
        self.bot_thread = None
        self.msg_queue = queue.Queue()
        
        # Start queue mechanism
        self.after(100, self.check_queue)

        # -- Grid Layout Configuration --
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # -- Sidebar --
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="IG Automator", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.settings_label = ctk.CTkLabel(self.sidebar_frame, text="Settings", anchor="w")
        self.settings_label.grid(row=1, column=0, padx=20, pady=(10, 0))

        self.batch_size_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Batch Size (100)")
        self.batch_size_entry.grid(row=2, column=0, padx=20, pady=(0, 10))
        self.batch_size_entry.insert(0, "100")
        
        self.limit_mode_switch = ctk.CTkSwitch(self.sidebar_frame, text="Run Until Empty")
        self.limit_mode_switch.grid(row=3, column=0, padx=20, pady=(0, 10))
        self.limit_mode_switch.select() 
        
        self.speed_label = ctk.CTkLabel(self.sidebar_frame, text="Selection Speed", anchor="w")
        self.speed_label.grid(row=4, column=0, padx=20, pady=(10, 0))
        self.speed_option = ctk.CTkOptionMenu(self.sidebar_frame, values=["Fast", "Medium", "Slow"])
        self.speed_option.grid(row=5, column=0, padx=20, pady=(0, 10))
        self.speed_option.set("Medium")
        
        self.stats_title_label = ctk.CTkLabel(self.sidebar_frame, text="Stats", anchor="w")
        self.stats_title_label.grid(row=6, column=0, padx=20, pady=(10, 0))
        
        self.total_unliked_label = ctk.CTkLabel(self.sidebar_frame, text="Total Unliked: 0", anchor="w", text_color="green")
        self.total_unliked_label.grid(row=7, column=0, padx=20, pady=(0, 10))
        
        # Theme Toggle
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=8, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=9, column=0, padx=20, pady=(10, 20))


        # -- Main Area --
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # Credentials Section
        self.creds_frame = ctk.CTkFrame(self.main_frame)
        self.creds_frame.pack(fill="x", pady=(0, 20))

        self.username_entry = ctk.CTkEntry(self.creds_frame, placeholder_text="Instagram Username", width=200)
        self.username_entry.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        self.password_entry = ctk.CTkEntry(self.creds_frame, placeholder_text="Password", show="*", width=200)
        self.password_entry.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        self.login_btn = ctk.CTkButton(self.creds_frame, text="Login / Start Session", command=self.start_login_thread)
        self.login_btn.pack(side="left", padx=10, pady=10)

        # Control Panel
        self.controls_frame = ctk.CTkFrame(self.main_frame)
        self.controls_frame.pack(fill="x", pady=(0, 20))

        self.status_label = ctk.CTkLabel(self.controls_frame, text="Status: Ready", text_color="gray")
        self.status_label.pack(side="top", pady=5)

        self.start_btn = ctk.CTkButton(self.controls_frame, text="Start Automation", command=self.start_automation_thread, state="disabled")
        self.start_btn.pack(side="left", padx=10, pady=10, expand=True)

        self.stop_btn = ctk.CTkButton(self.controls_frame, text="Stop", command=self.stop_automation, fg_color="red", hover_color="darkred")
        self.stop_btn.pack(side="left", padx=10, pady=10, expand=True)

        # Log Console
        self.log_textbox = ctk.CTkTextbox(self.main_frame, width=400)
        self.log_textbox.pack(fill="both", expand=True)
        self.log_textbox.insert("0.0", "--- System Log ---\nHint: First login will save session. Next time just click Login.\n")

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def check_queue(self):
        try:
            while True:
                msg_type, data = self.msg_queue.get_nowait()
                if msg_type == "log":
                    self.log_textbox.insert("end", f"{data}\n")
                    self.log_textbox.see("end")
                    self.status_label.configure(text=f"Status: {data}")
                elif msg_type == "stats":
                    self.total_unliked_label.configure(text=f"Total Unliked: {data}")
        except queue.Empty:
            pass
        finally:
            self.after(100, self.check_queue)

    def log_message(self, message):
        pass 

    def queue_log_message(self, message):
        self.msg_queue.put(("log", message))

    def queue_stats_update(self, total_count):
        self.msg_queue.put(("stats", total_count))
    
    # helper for main thread logging
    def log_direct(self, message):
         self.msg_queue.put(("log", message))

    def start_login_thread(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        # Headless mode removed
        threading.Thread(target=self.run_login, args=(username, password)).start()

    def run_login(self, username, password):
        self.login_btn.configure(state="disabled")
        self.log_direct("Attempting login/session restore...")
        
        # Always run headed
        success = self.bot.login(username, password, headless=False)
        
        if success:
            self.log_direct("Login/Session Verified!")
            self.start_btn.configure(state="normal")
        else:
            self.log_direct("Login Failed.")
            self.login_btn.configure(state="normal")

    def start_automation_thread(self):
        if self.bot.is_running:
            self.log_direct("Automation is already running.")
            return

        self.bot.stop_requested = False
        self.bot_thread = threading.Thread(target=self.run_automation)
        self.bot_thread.start()

    def run_automation(self):
        self.bot.is_running = True
        self.start_btn.configure(state="disabled")
        self.login_btn.configure(state="disabled")
        self.status_label.configure(text="Status: Running...")
        
        try:
            batch_val = self.batch_size_entry.get()
            batch_size = int(batch_val) if batch_val else 100
        except ValueError:
            self.bot.log("Invalid batch size. Using default 100.") 
            batch_size = 100
        
        speed_setting = self.speed_option.get()
        delay_range = (1, 3)
        if speed_setting == "Fast":
            delay_range = (0.2, 0.5) 
        elif speed_setting == "Medium":
            delay_range = (0.8, 1.5)
        elif speed_setting == "Slow":
            delay_range = (2.0, 4.0)
        
        run_until_empty = self.limit_mode_switch.get()
        
        iteration_count = 0
        while True:
            if self.bot.stop_requested:
                break
            
            iteration_count += 1
            self.bot.log(f"Starting batch {iteration_count} (Target: {batch_size})...")
            
            unliked_count = self.bot.process_unlike(batch_size=batch_size, delay_range=delay_range)
            
            if unliked_count == 0:
                self.bot.log("No posts unliked in this batch.")
                if run_until_empty and not self.bot.stop_requested:
                    self.bot.log("List might be empty. Finishing.")
                break

            if not run_until_empty:
                break
                
            self.bot.log("Batch complete. Continuing...")
            time.sleep(1.0) 
            
        self.bot.log("Automation finished.")
        self.after(0, lambda: self.finish_automation())

    def finish_automation(self):
        self.start_btn.configure(state="normal")
        self.login_btn.configure(state="normal")
        self.status_label.configure(text="Status: Ready")
        self.bot.is_running = False

    def stop_automation(self):
        if self.bot.is_running:
            self.bot.stop_requested = True
            self.log_direct("Stop requested... waiting for current step.")
            self.status_label.configure(text="Status: Stopping...")

    def on_close(self):
        self.stop_automation()
        if self.bot.driver:
            self.bot.close()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
