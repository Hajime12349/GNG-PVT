# pvt_app.py

import tkinter as tk
from tkinter import ttk, font, messagebox # messagebox はここでインポートされる
import random
import time
import datetime
import os
import json
import statistics

try:
    import matplotlib
    matplotlib.use('Agg') # GUIなしで実行するために重要
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("警告: matplotlibライブラリが見つかりません。グラフ機能は無効になります。`pip install matplotlib`でインストールしてください。")

try:
    from PIL import Image, ImageTk
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    print("警告: Pillowライブラリが見つかりません。グラフ表示機能は無効になります。`pip install Pillow`でインストールしてください。")


class PVTApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GNG-PVT")
        self.root.geometry("800x700")
        root.attributes('-fullscreen', True)

        self.data_dir = "recoded_data"
        if not os.path.exists(self.data_dir):
            try:
                os.makedirs(self.data_dir)
            except OSError as e:
                # テスト実行時はGUIのmessageboxを呼び出さないように注意
                print(f"エラー: データ保存ディレクトリの作成に失敗しました: {e}\nデータは保存されません。")
                # messagebox.showerror("エラー", f"データ保存ディレクトリの作成に失敗しました: {e}\nデータは保存されません。")
                self.data_dir = None

        self.setup_styles()

        self.start_frame = None
        self.test_frame = None
        self.results_frame = None

        # 設定可能変数
        self.target_number = 0 # ターゲット数字(0はランダム)
        self.target_trials = 25
        self.max_trials = 100
        self.min_interval_s = 0.5
        self.max_interval_s = 5.0
        self.response_limit_ms = 1500
        self.response_outlier_ms = 100

        # self.target_number = 0 # 初期化済み
        self.sequence=[]
        self.current_stimulus = 0
        self.previous_stimulus = 0
        self.number_counts = {i: 0 for i in range(1, 10)}
        self.total_trials_conducted = 0

        self.correct_go_responses = 0
        self.correct_no_go_responses = 0
        self.commission_errors = 0
        self.commission_outliers = 0 # 早すぎる反応
        self.omission_outliers = 0   # 遅すぎる反応(Go試行でのタイムアウト)
        self.reaction_times = []
        self.all_trial_data = []
        self.rt_std_dev_ms = None # 結果計算時に設定

        self.current_isi_ms = None
        self.feedback_duration_ms = 1000

        self.interval_timer_id = None
        self.reaction_window_timer_id = None
        self.feedback_clear_timer_id = None

        self.test_in_progress = False
        self.reaction_timer_start_time = 0
        self.stimulus_on_screen = False
        self.accepting_response = False

        self.graph_image_tk = None # ImageTk.PhotoImage オブジェクトを保持
        self.graph_label = None    # グラフを表示するラベルウィジェット

        self.show_start_screen()

    def setup_styles(self):
        self.title_font = font.Font(family="Helvetica", size=24, weight="bold")
        self.stimulus_font = font.Font(family="Arial", size=72, weight="bold")
        self.feedback_font = font.Font(family="Helvetica", size=20, weight="bold")
        self.text_font = font.Font(family="Helvetica", size=12)
        self.button_font = font.Font(family="Helvetica", size=14)
        self.small_text_font = font.Font(family="Helvetica", size=10)

        s = ttk.Style()
        s.configure("TButton", font=self.button_font, padding=10)
        s.configure("Large.TLabel", font=self.stimulus_font, padding=20)
        s.configure("Feedback.TLabel", font=self.feedback_font, padding=10)

    def clear_current_frame(self):
        if self.start_frame and self.start_frame.winfo_exists():
            self.start_frame.destroy()
        if self.test_frame and self.test_frame.winfo_exists():
            self.test_frame.destroy()
        if self.results_frame and self.results_frame.winfo_exists():
            self.results_frame.destroy()
        self.start_frame = self.test_frame = self.results_frame = None

        # Clear any pending timers
        if self.interval_timer_id:
            self.root.after_cancel(self.interval_timer_id)
            self.interval_timer_id = None
        if self.reaction_window_timer_id:
            self.root.after_cancel(self.reaction_window_timer_id)
            self.reaction_window_timer_id = None
        if self.feedback_clear_timer_id:
            self.root.after_cancel(self.feedback_clear_timer_id)
            self.feedback_clear_timer_id = None

    def show_start_screen(self):
        self.clear_current_frame()
        self.reset_test_variables()

        self.start_frame = ttk.Frame(self.root, padding="20")
        self.start_frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(self.start_frame, text="GNG-PVT", font=self.title_font).pack(pady=20)

        if self.target_number == 0: # Only set if not already set (e.g. for re-runs with same target)
            self.target_number = random.randint(1, 9)
        ttk.Label(self.start_frame, text=f"今回のターゲット数字: {self.target_number}", font=self.text_font).pack(pady=10)

        self.generate_sequence()

        explanation = (
            "画面に1から9までの数字が順番に表示されます。\n"
            f"ターゲット数字（今回は「{self.target_number}」）以外の数字が表示されたら、\n"
            "できるだけ速く「反応」ボタンを押してください。\n"
            f"ターゲット数字「{self.target_number}」が表示された場合は、\n"
            "ボタンを押さないでください。\n"
            "準備ができたら、「スタート」ボタンを押してください。"
        )
        ttk.Label(self.start_frame, text=explanation, font=self.text_font, justify=tk.LEFT).pack(pady=20)

        start_button = ttk.Button(self.start_frame, text="スタート", command=self.start_test, style="TButton")
        start_button.pack(pady=20)
        start_button.focus_set() # Set focus for Return key binding
        self.root.bind("<Return>", lambda event: start_button.invoke())

    def generate_sequence(self):
        self.sequence = [self.target_number] * self.target_trials
        number_range = range(1, 10)
        remaining_count = self.max_trials - self.target_trials
        other_numbers = [n for n in number_range if n != self.target_number]

        self.sequence += [random.choice(other_numbers) for _ in range(remaining_count)]

        random.shuffle(self.sequence)

    def reset_test_variables(self):
        # self.target_number remains unless explicitly reset (e.g. in show_start_screen if 0)
        self.current_stimulus = 0
        self.previous_stimulus = 0
        self.number_counts = {i: 0 for i in range(1, 10)}
        self.total_trials_conducted = 0
        self.correct_go_responses = 0
        self.correct_no_go_responses = 0
        self.commission_errors = 0
        self.commission_outliers = 0
        self.omission_outliers = 0
        self.reaction_times = []
        self.all_trial_data = []
        self.rt_std_dev_ms = None # Reset
        self.current_isi_ms = None
        self.test_in_progress = False
        self.stimulus_on_screen = False
        self.accepting_response = False
        self.graph_image_tk = None # Clear previous graph image reference

    def start_test(self):
        self.root.unbind("<Return>") # Unbind from start button
        self.test_in_progress = True
        self.show_test_screen()
        self.run_next_trial()

    def show_test_screen(self):
        self.clear_current_frame()
        self.test_frame = ttk.Frame(self.root, padding="20")
        self.test_frame.pack(expand=True, fill=tk.BOTH)

        center_frame = ttk.Frame(self.test_frame) # Frame to center content
        center_frame.pack(expand=True) # This will center the frame

        self.stimulus_label = ttk.Label(center_frame, text="", style="Large.TLabel", anchor=tk.CENTER)
        self.stimulus_label.pack(pady=40, ipady=20) # ipady for vertical size of the label itself

        self.feedback_label = ttk.Label(center_frame, text="", style="Feedback.TLabel", anchor=tk.CENTER)
        self.feedback_label.pack(pady=20)

        self.response_button = ttk.Button(center_frame, text="反応", command=self.handle_response_button, style="TButton")
        self.response_button.pack(pady=20)
        # Focus might be set in display_stimulus or here depending on flow

    def run_next_trial(self):
        if not self.test_in_progress:
            return

        if self.total_trials_conducted >= self.max_trials:
            self.end_test()
            return

        self.stimulus_label.config(text="") # Clear previous stimulus
        self.stimulus_on_screen = False
        self.accepting_response = False
        self.root.unbind("<Return>") # Unbind from previous trial's response button if any

        # ISI: Inter-Stimulus Interval
        interval_ms = random.randint(int(self.min_interval_s * 1000), int(self.max_interval_s * 1000))
        self.current_isi_ms = interval_ms
        self.interval_timer_id = self.root.after(interval_ms, self.display_stimulus)

    def select_stimulus(self):
        if not self.sequence: # Check if sequence is empty
            return None
        # Pop from the end for efficiency with list.pop()
        choiced_number = self.sequence.pop(-1)
        return choiced_number

    def display_stimulus(self):
        if not self.test_in_progress:
            return

        next_stimulus = self.select_stimulus()
        if next_stimulus is None: # No more stimuli in sequence
            self.end_test()
            return

        self.current_stimulus = next_stimulus
        self.stimulus_label.config(text=str(self.current_stimulus))
        self.stimulus_on_screen = True
        self.accepting_response = True # Start accepting response AFTER stimulus is on screen

        self.reaction_timer_start_time = time.perf_counter()
        self.number_counts[self.current_stimulus] += 1
        self.previous_stimulus = self.current_stimulus # Store for potential analysis

        self.response_button.focus_set() # Set focus to response button
        self.root.bind("<Return>", lambda event: self.response_button.invoke()) # Bind Enter to response button

        # Timer for response window (max reaction time)
        self.reaction_window_timer_id = self.root.after(self.response_limit_ms, self.handle_timeout)

    def handle_response_button(self, event=None):
        if not self.test_in_progress or not self.stimulus_on_screen or not self.accepting_response:
            return # Ignore premature or late presses

        if self.reaction_window_timer_id: # Cancel timeout timer
            self.root.after_cancel(self.reaction_window_timer_id)
            self.reaction_window_timer_id = None

        self.accepting_response = False # Stop accepting further responses for this trial
        self.root.unbind("<Return>") # Unbind Enter from response button

        rt_s = time.perf_counter() - self.reaction_timer_start_time
        rt_ms = round(rt_s * 1000)

        self.stimulus_label.config(text="") # Clear stimulus
        self.stimulus_on_screen = False

        is_target_stimulus = (self.current_stimulus == self.target_number)
        trial_outcome = {
            "trial_number": self.total_trials_conducted + 1,
            "pre_stimulus_interval_ms": self.current_isi_ms,
            "stimulus": self.current_stimulus,
            "is_target": 1 if is_target_stimulus else 0,
            "is_correct": 0, # Default to incorrect, update based on logic
            "reaction_time_ms": rt_ms
        }

        self.reaction_times.append(rt_ms) # Record all RTs for potential analysis
        if rt_ms < self.response_outlier_ms: # Response too fast
            self.show_feedback("TooFast!", "orange")
            self.commission_outliers += 1
            trial_outcome["is_correct"] = 0 # Or a specific code for outlier
        elif is_target_stimulus: # Pressed on target (NoGo trial) -> Commission Error
            self.show_feedback("Bad!", "red")
            self.commission_errors += 1
            trial_outcome["is_correct"] = 0
        else: # Pressed on non-target (Go trial) -> Correct Go
            self.show_feedback("Good!", "green")
            self.correct_go_responses += 1
            trial_outcome["is_correct"] = 1
        
        self.all_trial_data.append(trial_outcome)
        self.total_trials_conducted += 1
        self.feedback_clear_timer_id = self.root.after(self.feedback_duration_ms, self.clear_feedback_and_proceed)

    def handle_timeout(self):
        if not self.test_in_progress or not self.stimulus_on_screen or not self.accepting_response:
            return # Should not happen if logic is correct, but good safeguard

        self.reaction_window_timer_id = None # Timer already fired
        self.accepting_response = False
        self.root.unbind("<Return>")

        self.stimulus_label.config(text="")
        self.stimulus_on_screen = False

        is_target_stimulus = (self.current_stimulus == self.target_number)
        trial_outcome = {
            "trial_number": self.total_trials_conducted + 1,
            "pre_stimulus_interval_ms": self.current_isi_ms,
            "stimulus": self.current_stimulus,
            "is_target": 1 if is_target_stimulus else 0,
            "is_correct": 0,
            "reaction_time_ms": None # Timeout means no RT
        }

        if is_target_stimulus: # Correctly did not press on target (NoGo trial)
            self.show_feedback("Good!", "green")
            self.correct_no_go_responses += 1
            trial_outcome["is_correct"] = 1
        else: # Did not press on non-target (Go trial) -> Omission Error/Outlier
            self.show_feedback("TooLate!", "orange")
            self.omission_outliers += 1 # This is an omission error for a Go trial
            trial_outcome["is_correct"] = 0

        self.all_trial_data.append(trial_outcome)
        self.total_trials_conducted += 1
        self.feedback_clear_timer_id = self.root.after(self.feedback_duration_ms, self.clear_feedback_and_proceed)

    def show_feedback(self, message, color):
        self.feedback_label.config(text=message, foreground=color)

    def clear_feedback_and_proceed(self):
        self.feedback_label.config(text="")
        if self.feedback_clear_timer_id: # Should always be true if called from timer
            self.root.after_cancel(self.feedback_clear_timer_id)
            self.feedback_clear_timer_id = None

        # Check termination conditions again (e.g., if max_trials reached during feedback)
        if self.total_trials_conducted < self.max_trials:
            # This condition for early termination seems complex and might not be standard PVT/GNG
            # For simplicity, standard PVT runs for a fixed number of trials or time.
            # The "all_numbers_presented_max_times" logic is kept but might need review for GNG.
            all_numbers_presented_max_times = True
            # This check seems to try to ensure a certain distribution, but max_trials is the primary stop.
            # For GNG, it's more about Go/NoGo counts.
            # For now, let's assume self.max_trials is the main control.
            # If you need complex balancing, that logic would be here.
            # A simpler check:
            if sum(self.number_counts.values()) >= self.max_trials: # Alternative stop if counts fill up
                 self.end_test()
            else:
                 self.run_next_trial()
        else:
            self.end_test()

    def end_test(self):
        if not self.test_in_progress and self.total_trials_conducted > 0 : return # Avoid re-entry
        self.test_in_progress = False
        self.root.unbind("<Return>") # Clean up any lingering bindings
        
        # Cancel any active timers
        if self.interval_timer_id: self.root.after_cancel(self.interval_timer_id); self.interval_timer_id = None
        if self.reaction_window_timer_id: self.root.after_cancel(self.reaction_window_timer_id); self.reaction_window_timer_id = None
        if self.feedback_clear_timer_id: self.root.after_cancel(self.feedback_clear_timer_id); self.feedback_clear_timer_id = None

        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d_%H-%M")
        base_filename = os.path.join(self.data_dir, timestamp_str) if self.data_dir else timestamp_str

        json_filepath = None
        graph_filepath = None

        if self.data_dir: # Proceed only if data_dir is valid
            json_filepath = f"{base_filename}.json"
            self.save_data_to_json(json_filepath, now)

            if MATPLOTLIB_AVAILABLE:
                graph_filepath = f"{base_filename}.png"
                self.create_and_save_reaction_time_graph(graph_filepath)
            else:
                print("Matplotlibが無いためグラフは作成・保存されません。")
        else:
            print("データディレクトリが存在しないため、JSONとグラフは保存されません。")

        self.show_results_screen(json_filepath, graph_filepath)

    def save_data_to_json(self, filepath, timestamp_obj):
        total_correct_responses = self.correct_go_responses + self.correct_no_go_responses
        accuracy_percent = round((total_correct_responses / self.total_trials_conducted) * 100, 2) if self.total_trials_conducted > 0 else 0.0

        avg_rt = round(statistics.mean(self.reaction_times)) if self.reaction_times else None
        worst_rt = round(max(self.reaction_times)) if self.reaction_times else None
        self.rt_std_dev_ms = round(statistics.stdev(self.reaction_times)) if len(self.reaction_times) >= 2 else None

        data_to_save = {
            "datetime_iso": timestamp_obj.isoformat(),
            "test_settings": {
                "target_number": self.target_number,
                "response_limit_ms": self.response_limit_ms,
                "feedback_duration_ms": self.feedback_duration_ms,
                "min_interval_s": self.min_interval_s,
                "max_interval_s": self.max_interval_s,
                "configured_max_trials": self.max_trials
            },
            "summary_results": {
                "total_trials_conducted": self.total_trials_conducted,
                "correct_go_responses": self.correct_go_responses,
                "correct_no_go_responses": self.correct_no_go_responses,
                "commission_errors": self.commission_errors, # Pressed on target
                "outliers_commission_too_fast": self.commission_outliers, # Pressed too fast
                "outliers_omission_too_late": self.omission_outliers, # Timed out on non-target
                "accuracy_percentage": accuracy_percent,
                "average_reaction_time_ms": avg_rt,
                "worst_reaction_time_ms": worst_rt,
                "reaction_time_std_dev_ms": self.rt_std_dev_ms
            },
            "trials": self.all_trial_data
        }

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
            print(f"データが {filepath} に保存されました。")
        except Exception as e:
            # messagebox.showerror("JSON保存エラー", f"JSONファイルへの書き込み中にエラーが発生しました: {e}")
            print(f"JSON保存エラー: {e}")

    def create_and_save_reaction_time_graph(self, filepath):
        if not MATPLOTLIB_AVAILABLE or not self.reaction_times:
            if not self.reaction_times:
                print("反応時間データがないため、グラフは作成されません。")
            return

        try:
            plt.figure(figsize=(8, 4))
            # Plot only RTs from correct Go trials (where RT is meaningful for performance)
            # For GNG, RTs are typically from correct Go responses.
            # The self.reaction_times list currently stores RTs from *all* button presses.
            # Filter for correct Go responses if needed, or plot all recorded RTs.
            # Assuming self.reaction_times contains RTs primarily from intended Go responses (or all presses).
            
            # If you want to plot RTs only from correct Go responses:
            # correct_go_rts = [t['reaction_time_ms'] for t in self.all_trial_data if t['is_target'] == 0 and t['is_correct'] == 1 and t['reaction_time_ms'] is not None]
            # if not correct_go_rts:
            #     print("正反応のRTデータがないため、グラフは作成されません。")
            #     plt.close() # Close the figure if not used
            #     return
            # plt.plot(range(1, len(correct_go_rts) + 1), correct_go_rts, marker='o', linestyle='-')
            # plt.title("Reaction Time Over Correct Go Trials")
            # plt.xlabel("Correct Go Response Number")

            # Current implementation plots all recorded self.reaction_times:
            plt.plot(range(1, len(self.reaction_times) + 1), self.reaction_times, marker='o', linestyle='-')
            plt.title("Reaction Time Over Trials (Button Presses)")
            plt.xlabel("Button Press Number")

            plt.ylabel("Reaction Time (ms)")
            plt.grid(True)
            plt.tight_layout()
            plt.savefig(filepath)
            plt.close() # Close the figure to free memory
            print(f"グラフが {filepath} に保存されました。")
        except Exception as e:
            # messagebox.showerror("グラフ作成エラー", f"グラフの作成または保存中にエラーが発生しました: {e}")
            print(f"グラフ作成エラー: {e}")

    def show_results_screen(self, data_filepath=None, graph_filepath=None):
        self.clear_current_frame()
        self.results_frame = ttk.Frame(self.root, padding="10")
        self.results_frame.pack(expand=True, fill=tk.BOTH)

        main_results_frame = ttk.Frame(self.results_frame)
        main_results_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        graph_display_frame = ttk.Frame(self.results_frame, width=420) # Fixed width for graph
        graph_display_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=10)
        graph_display_frame.pack_propagate(False) # Prevent child widgets from resizing this frame

        ttk.Label(main_results_frame, text="テスト結果", font=self.title_font).pack(pady=10)

        total_correct_responses_val = self.correct_no_go_responses
        accuracy_percent = round((total_correct_responses_val / self.target_trials) * 100, 2) if self.total_trials_conducted > 0 else 0.0
        
        avg_rt_str = "N/A"; worst_rt_str = "N/A"; rt_std_dev_str = "N/A"
        # Use reaction_times from correct Go trials for meaningful stats, if desired
        # For now, using all recorded RTs as per save_data_to_json
        if self.reaction_times:
            avg_rt_val = round(statistics.mean(self.reaction_times))
            worst_rt_val = round(max(self.reaction_times))
            avg_rt_str = f"{avg_rt_val} ms"
            worst_rt_str = f"{worst_rt_val} ms"
            
            # self.rt_std_dev_ms should be calculated in end_test/save_data_to_json
            if self.rt_std_dev_ms is not None:
                rt_std_dev_str = f"{self.rt_std_dev_ms} ms"
            elif len(self.reaction_times) >= 2: # Fallback if not pre-calculated
                rt_std_dev_str = f"{round(statistics.stdev(self.reaction_times))} ms"
            else:
                rt_std_dev_str = "N/A (データ不足)"
        
        results_text = (
            f"総試行数: {self.total_trials_conducted}\n\n"
            f"正答率: {accuracy_percent} % \n"
            f"  正反応 (Go): {self.correct_go_responses}\n"
            f"  正抑制 (NoGo): {self.correct_no_go_responses}\n"
            f"外れ値 (早すぎ): {self.commission_outliers}\n"
            f"外れ値 (遅すぎ/見逃し): {self.omission_outliers}\n\n"
            f"平均反応時間 : {avg_rt_str}\n"
            f"最悪反応時間 : {worst_rt_str}\n"
            f"反応時間標準偏差: {rt_std_dev_str}\n"
        )
        ttk.Label(main_results_frame, text=results_text, font=self.text_font, justify=tk.LEFT).pack(pady=10, anchor='nw')

        if data_filepath:
            ttk.Label(main_results_frame, text=f"データ保存先: {os.path.abspath(data_filepath)}", font=self.small_text_font).pack(pady=5, anchor='nw')
        
        if graph_filepath and PILLOW_AVAILABLE and MATPLOTLIB_AVAILABLE and os.path.exists(graph_filepath):
            ttk.Label(main_results_frame, text=f"グラフ保存先: {os.path.abspath(graph_filepath)}", font=self.small_text_font).pack(pady=5, anchor='nw')
            try:
                img = Image.open(graph_filepath)
                basewidth = 400 # Desired width for the graph display
                wpercent = (basewidth / float(img.size[0]))
                hsize = int((float(img.size[1]) * float(wpercent)))
                img_resized = img.resize((basewidth, hsize), Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.Resampling.LANCZOS)
                self.graph_image_tk = ImageTk.PhotoImage(img_resized)
                
                if self.graph_label and self.graph_label.winfo_exists():
                    self.graph_label.config(image=self.graph_image_tk)
                else:
                    self.graph_label = ttk.Label(graph_display_frame, image=self.graph_image_tk)
                    self.graph_label.pack(pady=10, expand=True, anchor=tk.CENTER) # Center graph
            except Exception as e:
                print(f"グラフ画像の表示エラー: {e}")
                ttk.Label(graph_display_frame, text="グラフの表示に失敗しました。", font=self.text_font).pack(pady=10, expand=True, anchor=tk.CENTER)
        elif MATPLOTLIB_AVAILABLE and (not self.reaction_times or not graph_filepath or not os.path.exists(graph_filepath)):
             ttk.Label(graph_display_frame, text="反応時間データがないかグラフファイルが\n見つからないため表示されません。", font=self.text_font, justify=tk.CENTER).pack(pady=10, expand=True, anchor=tk.CENTER)
        elif not PILLOW_AVAILABLE or not MATPLOTLIB_AVAILABLE:
             ttk.Label(graph_display_frame, text="グラフ表示に必要なライブラリが\nないため表示できません。", font=self.text_font, justify=tk.CENTER).pack(pady=10, expand=True, anchor=tk.CENTER)


        button_frame = ttk.Frame(main_results_frame)
        button_frame.pack(pady=20, anchor='s') # Anchor south for bottom placement

        restart_button = ttk.Button(button_frame, text="もう一度行う", command=self.show_start_screen, style="TButton")
        restart_button.pack(side=tk.LEFT, padx=10)
        
        quit_button = ttk.Button(button_frame, text="終了する", command=self.quit_app, style="TButton")
        quit_button.pack(side=tk.LEFT, padx=10)

        restart_button.focus_set()
        self.root.bind("<Return>", lambda event: restart_button.invoke())

    def quit_app(self):
        # In a real app, messagebox.askokcancel would be used.
        # For testing, this is often mocked.
        # If messagebox is the real tkinter one (not mocked):
        if hasattr(messagebox, 'askokcancel') and callable(messagebox.askokcancel):
            if messagebox.askokcancel("確認", "アプリケーションを終了しますか？"):
                self._cleanup_timers_and_quit()
        else:
            # If messagebox is mocked or not available as expected, assume confirmation for cleanup
            print("Messagebox not available as expected or mocked, proceeding with quit actions.")
            self._cleanup_timers_and_quit()

    def _cleanup_timers_and_quit(self):
        # Ensure all timers are cancelled before quitting
        if self.interval_timer_id: self.root.after_cancel(self.interval_timer_id); self.interval_timer_id = None
        if self.reaction_window_timer_id: self.root.after_cancel(self.reaction_window_timer_id); self.reaction_window_timer_id = None
        if self.feedback_clear_timer_id: self.root.after_cancel(self.feedback_clear_timer_id); self.feedback_clear_timer_id = None
        
        if self.root and self.root.winfo_exists(): # Check if root window still exists
            self.root.quit()
            # self.root.destroy() # Use destroy if quit doesn't fully close in some contexts


if __name__ == "__main__":
    if not MATPLOTLIB_AVAILABLE:
        print("--- Matplotlibが利用できないため、グラフ関連機能は動作しません。 ---")
    if not PILLOW_AVAILABLE:
        print("--- Pillowが利用できないため、グラフ表示機能は動作しません。 ---")
        
    root = tk.Tk()
    app = PVTApp(root)
    root.mainloop()