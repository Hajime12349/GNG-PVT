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
    app.max_trials = 10
    app.target_trials = 3
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
    app.generate_sequence()
    seq = app.sequence
    assert len(seq) == 10
    assert seq.count(5) == 3


def test_go_response(app, root, monkeypatch):
    app.target_number = 9
    app.sequence = [1]
    simulate_rt(monkeypatch, 0.0, 0.2)
    app.start_test()
    root.update()
    app.display_stimulus()
    app.handle_response_button()
    assert app.correct_go_responses == 1
    assert app.all_trial_data[0]['is_correct'] == 1


def test_too_fast_commission(app, root, monkeypatch):
    app.target_number = 2
    app.sequence = [2]
    simulate_rt(monkeypatch, 0.0, 0.05)
    app.start_test()
    root.update()
    app.display_stimulus()
    app.handle_response_button()
    assert app.commission_outliers == 1
    assert app.all_trial_data[0]['is_correct'] == 0


def test_commission_error(app, root, monkeypatch):
    app.target_number = 7
    app.sequence = [7]
    simulate_rt(monkeypatch, 0.0, 0.3)
    app.start_test()
    root.update()
    app.display_stimulus()
    app.handle_response_button()
    assert app.commission_errors == 1
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


def test_mixed_performance_summary(app, tmp_path):
    app.data_dir = str(tmp_path)
    app.test_in_progress = True
    app.total_trials_conducted = 5
    app.correct_go_responses = 2
    app.correct_no_go_responses = 1
    app.commission_errors = 1
    app.omission_outliers = 1
    app.commission_outliers = 0
    rts = [180, 220]
    app.reaction_times = rts.copy()
    app.all_trial_data = [
        {'trial_number':1, 'pre_stimulus_interval_ms':100, 'stimulus':1, 'is_target':0, 'is_correct':1, 'reaction_time_ms':180},
        {'trial_number':2, 'pre_stimulus_interval_ms':120, 'stimulus':1, 'is_target':0, 'is_correct':1, 'reaction_time_ms':220},
        {'trial_number':3, 'pre_stimulus_interval_ms':150, 'stimulus':2, 'is_target':1, 'is_correct':1, 'reaction_time_ms':None},
        {'trial_number':4, 'pre_stimulus_interval_ms':180, 'stimulus':2, 'is_target':1, 'is_correct':0, 'reaction_time_ms':None},
        {'trial_number':5, 'pre_stimulus_interval_ms':200, 'stimulus':3, 'is_target':0, 'is_correct':0, 'reaction_time_ms':None}
    ]
    app.end_test()
    json_file = next(f for f in os.listdir(app.data_dir) if f.endswith('.json'))
    with open(os.path.join(app.data_dir, json_file), 'r', encoding='utf-8') as f:
        data = json.load(f)
    summary = data['summary_results']
    assert summary['accuracy_percentage'] == 60.0
    assert summary['average_reaction_time_ms'] == 200
    assert summary['worst_reaction_time_ms'] == 220
    import statistics
    assert summary['reaction_time_std_dev_ms'] == round(statistics.stdev(rts))


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


def test_single_rt_statistics(app, tmp_path):
    app.data_dir = str(tmp_path)
    app.test_in_progress = True
    app.total_trials_conducted = 1
    app.correct_go_responses = 1
    app.correct_no_go_responses = 0
    app.reaction_times = [250]
    app.all_trial_data = [
        {'trial_number':1, 'pre_stimulus_interval_ms':100, 'stimulus':1, 'is_target':0, 'is_correct':1, 'reaction_time_ms':250}
    ]
    app.end_test()
    json_file = next(f for f in os.listdir(app.data_dir) if f.endswith('.json'))
    with open(os.path.join(app.data_dir, json_file), 'r', encoding='utf-8') as f:
        data = json.load(f)
    summary = data['summary_results']
    assert summary['average_reaction_time_ms'] == 250
    assert summary['worst_reaction_time_ms'] == 250
    assert summary['reaction_time_std_dev_ms'] is None


def test_no_trials_statistics(app, tmp_path):
    app.data_dir = str(tmp_path)
    app.test_in_progress = True
    app.total_trials_conducted = 0
    app.correct_go_responses = 0
    app.correct_no_go_responses = 0
    app.reaction_times = []
    app.all_trial_data = []
    app.end_test()
    json_file = next(f for f in os.listdir(app.data_dir) if f.endswith('.json'))
    with open(os.path.join(app.data_dir, json_file), 'r', encoding='utf-8') as f:
        data = json.load(f)
    summary = data['summary_results']
    assert summary['accuracy_percentage'] == 0.0
    assert summary['average_reaction_time_ms'] is None
    assert summary['worst_reaction_time_ms'] is None
    assert summary['reaction_time_std_dev_ms'] is None
