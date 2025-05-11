import unittest
from unittest.mock import MagicMock, patch, mock_open, call
import tkinter as tk
import os
import json
import time
import random
import datetime

# gng_pvt.py から PVTApp クラスと関連するグローバル変数をインポート
from gng_pvt import PVTApp # <--- 修正点

# PVTApp 内の print 文をテスト中は無効化（任意）
# import builtins
# mock_print = MagicMock()
# @patch('builtins.print', mock_print)


class MockTk(MagicMock):
    """tkinter.Tkの基本的なメソッドをモックするクラス"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.after_calls = []
        self.bindings = {}
        self.attributes_calls = []
        self.quit_called = False
        self.title_val = ""
        self.geometry_val = ""

        # tk.Frameなどのウィジェットモックを返すように設定
        self.Frame = MagicMock(spec=tk.Frame)
        self.Label = MagicMock(spec=tk.Label)
        self.Button = MagicMock(spec=tk.Button)
        self.Style = MagicMock()
        self.configure = MagicMock()
        self.Style.return_value.configure = self.configure

        # ttk のモック
        ttk_mock = MagicMock()
        ttk_mock.Frame = MagicMock(return_value=MagicMock(spec=tk.Frame))
        ttk_mock.Label = MagicMock(return_value=MagicMock(spec=tk.Label))
        ttk_mock.Button = MagicMock(return_value=MagicMock(spec=tk.Button))
        ttk_mock.Style = MagicMock(return_value=self.Style.return_value)
        self.patcher_ttk = patch('gng_pvt.ttk', ttk_mock) # <--- 修正点


    def after(self, delay_ms, callback, *args):
        timer_id = f"timer_{len(self.after_calls)}"
        self.after_calls.append({
            'id': timer_id,
            'delay_ms': delay_ms,
            'callback': callback,
            'args': args,
            'cancelled': False
        })
        return timer_id

    def after_cancel(self, timer_id):
        for call_info in self.after_calls:
            if call_info['id'] == timer_id:
                call_info['cancelled'] = True
                return

    def bind(self, event, func):
        self.bindings[event] = func

    def unbind(self, event):
        if event in self.bindings:
            del self.bindings[event]

    def attributes(self, *args):
        self.attributes_calls.append(args)

    def quit(self):
        self.quit_called = True

    def title(self, title_str):
        self.title_val = title_str

    def geometry(self, geometry_str):
        self.geometry_val = geometry_str

    def run_pending_after_callbacks(self):
        pending_calls = [call for call in self.after_calls if not call.get('executed') and not call['cancelled']]
        for call_info in pending_calls:
            if not call_info['cancelled']:
                call_info['callback'](*call_info['args'])
                call_info['executed'] = True
    
    def get_latest_after_callback(self):
        active_calls = [call for call in self.after_calls if not call['cancelled'] and not call.get('executed')]
        if active_calls:
            return active_calls[-1]
        return None

    def start_mocking_ttk(self):
        self.patcher_ttk.start()

    def stop_mocking_ttk(self):
        self.patcher_ttk.stop()


class TestPVTApp(unittest.TestCase):

    def setUp(self):
        self.mock_root = MockTk()
        self.mock_root.start_mocking_ttk()

        self.patch_matplotlib_available = patch('gng_pvt.MATPLOTLIB_AVAILABLE', True) # <--- 修正点
        self.patch_pillow_available = patch('gng_pvt.PILLOW_AVAILABLE', True) # <--- 修正点
        self.mock_matplotlib_available = self.patch_matplotlib_available.start()
        self.mock_pillow_available = self.patch_pillow_available.start()

        self.patch_plt_show = patch('gng_pvt.plt.show', MagicMock()) # <--- 修正点
        self.mock_plt_show = self.patch_plt_show.start()
        
        self.patch_plt_savefig = patch('gng_pvt.plt.savefig', MagicMock()) # <--- 修正点
        self.mock_plt_savefig = self.patch_plt_savefig.start()

        self.patch_plt_close = patch('gng_pvt.plt.close', MagicMock()) # <--- 修正点
        self.mock_plt_close = self.patch_plt_close.start()
        
        self.patch_image_open = patch('gng_pvt.Image.open', MagicMock(return_value=MagicMock(size=(100,100), resize=MagicMock(), LANCZOS=None))) # <--- 修正点
        self.mock_image_open = self.patch_image_open.start()

        self.patch_image_tk_photoimage = patch('gng_pvt.ImageTk.PhotoImage', MagicMock()) # <--- 修正点
        self.mock_image_tk_photoimage = self.patch_image_tk_photoimage.start()

        self.patch_os_path_exists = patch('gng_pvt.os.path.exists') # <--- 修正点
        self.mock_os_path_exists = self.patch_os_path_exists.start()
        
        self.patch_os_makedirs = patch('gng_pvt.os.makedirs') # <--- 修正点
        self.mock_os_makedirs = self.patch_os_makedirs.start()

        self.patch_messagebox = patch('gng_pvt.messagebox') # <--- 修正点
        self.mock_messagebox = self.patch_messagebox.start()

        self.patch_open = patch('gng_pvt.open', mock_open()) # <--- 修正点
        self.mock_file_open = self.patch_open.start()
        
        self.patch_time_perf_counter = patch('gng_pvt.time.perf_counter') # <--- 修正点
        self.mock_time_perf_counter = self.patch_time_perf_counter.start()

        self.patch_random_randint = patch('gng_pvt.random.randint') # <--- 修正点
        self.mock_random_randint = self.patch_random_randint.start()
        
        self.patch_random_choice = patch('gng_pvt.random.choice') # <--- 修正点
        self.mock_random_choice = self.patch_random_choice.start()

        self.patch_random_shuffle = patch('gng_pvt.random.shuffle', side_effect=lambda x: x) # <--- 修正点
        self.mock_random_shuffle = self.patch_random_shuffle.start()

        self.mock_os_path_exists.return_value = False
        self.mock_random_randint.return_value = 3
        self.app = PVTApp(self.mock_root)

    def tearDown(self):
        self.patch_os_path_exists.stop()
        self.patch_os_makedirs.stop()
        self.patch_messagebox.stop()
        self.patch_open.stop()
        self.patch_time_perf_counter.stop()
        self.patch_random_randint.stop()
        self.patch_random_choice.stop()
        self.patch_random_shuffle.stop()
        self.patch_matplotlib_available.stop()
        self.patch_pillow_available.stop()
        self.patch_plt_show.stop()
        self.patch_plt_savefig.stop()
        self.patch_plt_close.stop()
        self.patch_image_open.stop()
        self.patch_image_tk_photoimage.stop()
        self.mock_root.stop_mocking_ttk()

    def test_01_initialization(self):
        self.assertEqual(self.app.root.title_val, "GNG-PVT")
        self.assertIn(call('-fullscreen', True), self.app.root.attributes_calls)
        self.assertEqual(self.app.max_trials, 90)
        self.assertTrue(os.path.exists(self.app.data_dir) or self.mock_os_makedirs.called)
        self.assertTrue(1 <= self.app.target_number <= 9)
        self.assertTrue(len(self.app.sequence) == self.app.max_trials)

    def test_02_generate_sequence(self):
        self.app.max_trials = 18
        self.app.target_number = 3
        self.app.generate_sequence()
        self.assertEqual(len(self.app.sequence), 18)
        expected_target_count = 18 // 9
        self.assertEqual(self.app.sequence.count(self.app.target_number), expected_target_count)
        for i in range(len(self.app.sequence) - 1):
            if self.app.sequence[i] == self.app.target_number and self.app.sequence[i+1] == self.app.target_number:
                self.fail("Target number should not be consecutive.")

    def test_03_start_test_and_first_trial_setup(self):
        self.mock_random_randint.side_effect = [self.app.target_number, 1000]
        self.app.start_test()
        self.assertTrue(self.app.test_in_progress)
        cb_info = self.mock_root.get_latest_after_callback()
        self.assertIsNotNone(cb_info)
        self.assertEqual(cb_info['callback'], self.app.display_stimulus)
        self.assertEqual(cb_info['delay_ms'], 1000)

    def _run_to_stimulus_display(self, stimulus_to_show, isi_ms=1000):
        self.app.sequence = [stimulus_to_show] + [ (i % 9) + 1 for i in range(self.app.max_trials -1) ]
        self.mock_random_randint.return_value = isi_ms
        self.app.start_test()
        display_stimulus_call = self.mock_root.get_latest_after_callback()
        self.assertIsNotNone(display_stimulus_call, "display_stimulus not scheduled")
        self.assertEqual(display_stimulus_call['callback'], self.app.display_stimulus)
        self.mock_time_perf_counter.return_value = 1.0
        display_stimulus_call['callback'](*display_stimulus_call['args'])
        self.assertTrue(self.app.stimulus_on_screen)
        self.assertTrue(self.app.accepting_response)
        self.assertEqual(self.app.current_stimulus, stimulus_to_show)
        self.assertEqual(self.app.reaction_timer_start_time, 1.0)
        handle_timeout_call = self.mock_root.get_latest_after_callback()
        self.assertIsNotNone(handle_timeout_call, "handle_timeout not scheduled")
        self.assertEqual(handle_timeout_call['callback'], self.app.handle_timeout)
        return handle_timeout_call

    def test_04_go_trial_correct_response(self):
        non_target_stimulus = (self.app.target_number % 9) + 1
        self._run_to_stimulus_display(non_target_stimulus)
        self.mock_time_perf_counter.return_value = 1.200
        self.app.handle_response_button()
        self.assertEqual(self.app.correct_go_responses, 1)
        self.assertEqual(len(self.app.reaction_times), 1)
        self.assertAlmostEqual(self.app.reaction_times[0], 200)
        self.assertIn("Good!", self.app.feedback_label.config.call_args[1]['text'])
        feedback_clear_call = self.mock_root.get_latest_after_callback()
        self.assertIsNotNone(feedback_clear_call)
        self.assertEqual(feedback_clear_call['callback'], self.app.clear_feedback_and_proceed)

    def test_05_no_go_trial_commission_error(self):
        target_stimulus = self.app.target_number
        self._run_to_stimulus_display(target_stimulus)
        self.mock_time_perf_counter.return_value = 1.250
        self.app.handle_response_button()
        self.assertEqual(self.app.commission_errors, 1)
        self.assertEqual(len(self.app.reaction_times), 1)
        self.assertAlmostEqual(self.app.reaction_times[0], 250)
        self.assertIn("Bad!", self.app.feedback_label.config.call_args[1]['text'])

    def test_06_go_trial_timeout_omission(self):
        non_target_stimulus = (self.app.target_number % 9) + 1
        handle_timeout_call = self._run_to_stimulus_display(non_target_stimulus)
        handle_timeout_call['callback'](*handle_timeout_call['args'])
        self.assertEqual(self.app.omission_outliers, 1)
        self.assertEqual(len(self.app.reaction_times), 0)
        self.assertIn("TooLate!", self.app.feedback_label.config.call_args[1]['text'])

    def test_07_no_go_trial_correct_timeout(self):
        target_stimulus = self.app.target_number
        handle_timeout_call = self._run_to_stimulus_display(target_stimulus)
        handle_timeout_call['callback'](*handle_timeout_call['args'])
        self.assertEqual(self.app.correct_no_go_responses, 1)
        self.assertEqual(len(self.app.reaction_times), 0)
        self.assertIn("Good!", self.app.feedback_label.config.call_args[1]['text'])

    def test_08_too_fast_response(self):
        non_target_stimulus = (self.app.target_number % 9) + 1
        self._run_to_stimulus_display(non_target_stimulus)
        self.mock_time_perf_counter.return_value = 1.050
        self.app.handle_response_button()
        self.assertEqual(self.app.commission_outliers, 1)
        self.assertEqual(len(self.app.reaction_times), 1)
        self.assertAlmostEqual(self.app.reaction_times[0], 50)
        self.assertIn("TooFast!", self.app.feedback_label.config.call_args[1]['text'])

    def test_09_end_test_and_save_data(self):
        self.app.total_trials_conducted = 2
        self.app.correct_go_responses = 1
        self.app.reaction_times = [200]
        self.app.commission_errors = 1
        self.app.all_trial_data = [
            {"trial_number": 1, "stimulus": 1, "is_target": 0, "is_correct": 1, "reaction_time_ms": 200},
            {"trial_number": 2, "stimulus": self.app.target_number, "is_target": 1, "is_correct": 0, "reaction_time_ms": 250}
        ]
        self.app.rt_std_dev_ms = 0 # statistics.stdevはモックされていないので、手動で設定

        self.app.MATPLOTLIB_AVAILABLE = True
        self.app.PILLOW_AVAILABLE = True

        with patch('gng_pvt.datetime') as mock_datetime: # <--- 修正点
            mock_now = datetime.datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.datetime.now.return_value = mock_now
            self.app.end_test()

        self.assertFalse(self.app.test_in_progress)
        self.mock_file_open.assert_called_once()
        expected_filename = os.path.join(self.app.data_dir, "2023-01-01_12-00.json")
        self.assertEqual(self.mock_file_open.call_args[0][0], expected_filename)
        self.mock_plt_savefig.assert_called_once()
        expected_graph_filename = os.path.join(self.app.data_dir, "2023-01-01_12-00.png")
        self.assertEqual(self.mock_plt_savefig.call_args[0][0], expected_graph_filename)
        self.mock_plt_close.assert_called_once()
        self.assertIsNotNone(self.app.results_frame)

    def test_10_quit_app(self):
        self.mock_messagebox.askokcancel.return_value = True
        self.app.quit_app()
        self.mock_messagebox.askokcancel.assert_called_once_with("確認", "アプリケーションを終了しますか？")
        self.assertTrue(self.app.root.quit_called)

    def test_11_data_dir_creation_failure(self):
        self.mock_os_path_exists.return_value = False
        self.mock_os_makedirs.side_effect = OSError("Test permission denied")
        
        with patch('gng_pvt.os.path.exists', return_value=False), \
             patch('gng_pvt.os.makedirs', side_effect=OSError("Test permission denied")): # <--- 修正点
            app_with_error = PVTApp(self.mock_root)
            self.assertIsNone(app_with_error.data_dir)
            self.mock_messagebox.showerror.assert_called_once()


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)