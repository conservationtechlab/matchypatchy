# credit to https://github.com/frederikpahde/xai-canonization for the basis of this canonization
# this implementation is modified to work with timm models as well as torch models

import torch
from torch.nn import functional as F
from zennit import canonizers as canonizers
from zennit import layer as zlayer

from torchvision.models.efficientnet import MBConv
from torchvision.ops.misc import SqueezeExcitation
from timm.models._efficientnet_blocks import SqueezeExcite

class SignalOnlyGate(torch.autograd.Function):

    @staticmethod
    def forward(ctx,x1,x2):
        return x1*x2 

    @staticmethod
    def backward(ctx,grad_output):
        return torch.zeros_like(grad_output), grad_output


class SECanonizer(canonizers.AttributeCanonizer):
    def __init__(self):
        super().__init__(self._attribute_map)

    @classmethod
    def _attribute_map(cls, name, module):
        if isinstance(module, SqueezeExcitation):
            attributes = {
                'forward': cls.forward.__get__(module),
                'fn_gate': SignalOnlyGate()
            }
            return attributes
        elif isinstance(module, SqueezeExcite):
            attributes = {
                'forward': cls.forward.__get__(module),
                'fn_gate': SignalOnlyGate()
            }
            return attributes
        return None

    @staticmethod
    def forward(self, input):
        if isinstance(self, SqueezeExcitation):
            scale = self._scale(input)
            return self.fn_gate.apply(scale, input)
        else:
            scale = input.mean((2, 3), keepdim=True)
            scale = self.conv_reduce(scale)
            scale = self.act1(scale)
            scale = self.conv_expand(scale)
            scale = self.gate(scale)
            return self.fn_gate.apply(scale, input)

class MBConvCanonizer(canonizers.AttributeCanonizer):
    '''Canonizer specifically for MBConvBlock of Mobile Net v2 type models.'''

    def __init__(self):
        super().__init__(self._attribute_map)

    @classmethod
    def _attribute_map(cls, name, module):
        #print("class", module.__class__)
        if isinstance(module, MBConv):
            print("hi!! i'm here!!")
            attributes = {
                'forward': cls.forward.__get__(module),
                'canonizer_sum': zlayer.Sum()
            }
            return attributes
        return None

    @staticmethod
    def forward(self, input):
        result = self.block(input)
        if self.use_res_connect:
            result = self.stochastic_depth(result)

            # result += input
            result = torch.stack([input, result], dim=-1)
            result = self.canonizer_sum(result)
        return result

class EfficientNetCanonizer(canonizers.CompositeCanonizer):
    def __init__(self):
        super().__init__((
            SECanonizer(),
            MBConvCanonizer(),
        ))

class EfficientNetBNCanonizer(canonizers.CompositeCanonizer):
    def __init__(self):
        super().__init__((
            SECanonizer(),
            MBConvCanonizer(),
            canonizers.SequentialMergeBatchNorm()
        ))