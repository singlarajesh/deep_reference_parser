# Changelog 

## 2020.3.2 - Pre-release

* Adds parse command that can be called with `python -m deep_reference_parser parse` 
* Rename predict command to 'split' which can be called with `python -m deep_reference_parser parse` 
* Squashes most `tensorflow`, `keras_contrib`, and `numpy` warnings in `__init__.py` resulting from old versions and soon-to-be deprecated functions.
* Reduces verbosity of logging, improving CLI clarity.

## 2020.2.0 - Pre-release

First release. Features train and predict functions tested mainly for the task of labelling reference (e.g. academic references) spans in policy documents (e.g. documents produced by government, NGOs, etc).
