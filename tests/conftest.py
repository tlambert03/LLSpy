import pytest

from llspy.libcudawrapper import cudaLib

requires_cuda = pytest.mark.skipif(not cudaLib, reason="Cannot test without CUDA")
