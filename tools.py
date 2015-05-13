# -*- coding: utf-8 -*-
__author__ = 'Sigbjorn Grini'

"""
Some tool functions used in the thesis.

"""
import numpy as np

def mbd(model, measure):
    return (model - measure).mean() / measure.mean() * 100

def mae(model, measure):
    return abs((model - measure)).mean() / measure.mean() * 100

def rmsd(model, measure):
    return np.sqrt(((model - measure) ** 2).mean()) / measure.mean() * 100

def relative_change(x, ref):
    return (x - ref) / ref * 100