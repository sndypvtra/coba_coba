"""Calibration and measurement scripts supporting the two pipelines.

``probe_prompts``       sweep prompt wording and confidence against a clip
``tune_thresholds``     measure how late an object is first detected on entry
``perturbation_test``   measure what a moved camera costs the fill inspection

None of these are needed to run a case; they are how the constants the cases
depend on were arrived at.
"""
