import os
import json
import tkinter as tk
import time
import pytest
import matplotlib
matplotlib.use('Agg')

import gng_pvt

@pytest.fixture
def root(monkeypatch):
    root = tk.Tk()
    root.withdraw()
    monkeypatch.setattr(root, 'attributes', lambda *args, **kwargs: None)
    return root

@pytest.fixture
def app(tmp_path, root):
    app = gng_pvt.PVTApp(root)
    app.data_dir = str(tmp_path)
    os.makedirs(app.data_dir, exist_ok=True)
    app.max_trials = 2
    app.target_trials = 1
    app.response_limit_ms = 500
    app.feedback_duration_ms = 10
    return app


def simulate_rt(monkeypatch, start, end):
    calls = [start, end]
    def perf():
        return calls.pop(0)
    monkeypatch.setattr(time, 'perf_counter', perf)


def test_sequence_generation(app):
    app.target_number = 5
    app.max_trials = 10
    app.target_trials = 3
    app.generate_sequence()
    seq = app.sequence
    assert len(seq) == 10
    assert seq.count(5) == 3


def test_go_response(app, root, monkeypatch):
    # 非ターゲット刺激に対し200msで反応 → Correct Go
    app.target_number = 9
    app.sequence = [1]
    # 反応時間モックを先にセット
    simulate_rt(monkeypatch, 0.0, 0.2)
    app.start_test()
    root.update()
    app.display_stimulus()
    app.handle_response_button()
    assert app.correct_go_responses == 1
    assert app.all_trial_data[0]['is_correct'] == 1


def test_too_fast_commission(app, root, monkeypatch):
    # ターゲット刺激に対し50msで反応 → TooFast
    app.target_number = 2
    app.sequence = [2]
    simulate_rt(monkeypatch, 0.0, 0.05)
    app.start_test()
    root.update()
    app.display_stimulus()
    app.handle_response_button()
    assert app.commission_outliers == 1
    assert app.all_trial_data[0]['is_correct'] == 0


def test_timeout_nogo_correct(app, root):
    app.target_number = 3
    app.sequence = [3]
    app.start_test()
    root.update()
    app.display_stimulus()
    app.handle_timeout()
    assert app.correct_no_go_responses == 1
    assert app.all_trial_data[0]['is_correct'] == 1


def test_timeout_go_omission(app, root):
    app.target_number = 4
    app.sequence = [5]
    app.start_test()
    root.update()
    app.display_stimulus()
    app.handle_timeout()
    assert app.omission_outliers == 1
    assert app.all_trial_data[0]['is_correct'] == 0


def test_end_test_saves_json_and_graph(app):
    app.test_in_progress = True
    app.total_trials_conducted = 2
    app.correct_go_responses = 1
    app.correct_no_go_responses = 0
    app.commission_errors = 0
    app.commission_outliers = 0
    app.omission_outliers = 1
    app.reaction_times = [150, 200]
    app.all_trial_data = [
        {'trial_number':1, 'pre_stimulus_interval_ms':100, 'stimulus':1, 'is_target':0, 'is_correct':1, 'reaction_time_ms':150},
        {'trial_number':2, 'pre_stimulus_interval_ms':200, 'stimulus':2, 'is_target':1, 'is_correct':0, 'reaction_time_ms':None}
    ]
    app.end_test()
    files = os.listdir(app.data_dir)
    assert any(f.endswith('.json') for f in files)
    assert any(f.endswith('.png') for f in files)
