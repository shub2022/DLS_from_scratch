# -*- coding: utf-8 -*-
"""Untitled11.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1HfjaFn0lPOnq0c_-ZgoaGVJD2HbQgEfH
"""

from network import Module
import numpy as np

class Relu(Module):
    def __init__(self):
        pass

    def forward(self, x):
        return np.maximum(x, 0)

    def backward(self, grad, lr, prev_hidden):
        return np.multiply(grad, np.heaviside(prev_hidden, 0))