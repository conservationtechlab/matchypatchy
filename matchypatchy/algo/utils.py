"""
Utility funtions for running inference 

"""
import torch


def is_cuda_available():
    return torch.cuda.is_available()
