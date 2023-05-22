# Copyright The Lightning team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from functools import partial

import numpy as np
import pytest
import torch
from scipy.special import expit as sigmoid
from sklearn.metrics import confusion_matrix as sk_confusion_matrix

from torchmetrics.classification.confusion_matrix import (
    BinaryConfusionMatrix,
    MulticlassConfusionMatrix,
    MultilabelConfusionMatrix,
)
from torchmetrics.functional.classification.confusion_matrix import (
    binary_confusion_matrix,
    multiclass_confusion_matrix,
    multilabel_confusion_matrix,
)
from unittests import NUM_CLASSES, THRESHOLD
from unittests.classification.inputs import _binary_cases, _multiclass_cases, _multilabel_cases
from unittests.helpers import seed_all
from unittests.helpers.testers import MetricTester, inject_ignore_index, remove_ignore_index

seed_all(42)


def _sklearn_confusion_matrix_binary(preds, target, normalize=None, ignore_index=None):
    preds = preds.view(-1).numpy()
    target = target.view(-1).numpy()
    if np.issubdtype(preds.dtype, np.floating):
        if not ((preds > 0) & (preds < 1)).all():
            preds = sigmoid(preds)
        preds = (preds >= THRESHOLD).astype(np.uint8)
    target, preds = remove_ignore_index(target, preds, ignore_index)
    return sk_confusion_matrix(y_true=target, y_pred=preds, labels=[0, 1], normalize=normalize)


@pytest.mark.parametrize("input", _binary_cases)
class TestBinaryConfusionMatrix(MetricTester):
    """Test class for `BinaryConfusionMatrix` metric."""

    @pytest.mark.parametrize("normalize", ["true", "pred", "all", None])
    @pytest.mark.parametrize("ignore_index", [None, -1, 0])
    @pytest.mark.parametrize("ddp", [True, False])
    def test_binary_confusion_matrix(self, input, ddp, normalize, ignore_index):
        """Test class implementation of metric."""
        preds, target = input
        if ignore_index is not None:
            target = inject_ignore_index(target, ignore_index)
        self.run_class_metric_test(
            ddp=ddp,
            preds=preds,
            target=target,
            metric_class=BinaryConfusionMatrix,
            reference_metric=partial(_sklearn_confusion_matrix_binary, normalize=normalize, ignore_index=ignore_index),
            metric_args={
                "threshold": THRESHOLD,
                "normalize": normalize,
                "ignore_index": ignore_index,
            },
        )

    @pytest.mark.parametrize("normalize", ["true", "pred", "all", None])
    @pytest.mark.parametrize("ignore_index", [None, -1, 0])
    def test_binary_confusion_matrix_functional(self, input, normalize, ignore_index):
        """Test functional implementation of metric."""
        preds, target = input
        if ignore_index is not None:
            target = inject_ignore_index(target, ignore_index)
        self.run_functional_metric_test(
            preds=preds,
            target=target,
            metric_functional=binary_confusion_matrix,
            reference_metric=partial(_sklearn_confusion_matrix_binary, normalize=normalize, ignore_index=ignore_index),
            metric_args={
                "threshold": THRESHOLD,
                "normalize": normalize,
                "ignore_index": ignore_index,
            },
        )

    def test_binary_confusion_matrix_differentiability(self, input):
        """Test the differentiability of the metric, according to its `is_differentiable` attribute."""
        preds, target = input
        self.run_differentiability_test(
            preds=preds,
            target=target,
            metric_module=BinaryConfusionMatrix,
            metric_functional=binary_confusion_matrix,
            metric_args={"threshold": THRESHOLD},
        )

    @pytest.mark.parametrize("dtype", [torch.half, torch.double])
    def test_binary_confusion_matrix_dtype_cpu(self, input, dtype):
        """Test dtype support of the metric on CPU."""
        preds, target = input

        if (preds < 0).any() and dtype == torch.half:
            pytest.xfail(reason="torch.sigmoid in metric does not support cpu + half precision")
        self.run_precision_test_cpu(
            preds=preds,
            target=target,
            metric_module=BinaryConfusionMatrix,
            metric_functional=binary_confusion_matrix,
            metric_args={"threshold": THRESHOLD},
            dtype=dtype,
        )

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="test requires cuda")
    @pytest.mark.parametrize("dtype", [torch.half, torch.double])
    def test_binary_confusion_matrix_dtype_gpu(self, input, dtype):
        """Test dtype support of the metric on GPU."""
        preds, target = input
        self.run_precision_test_gpu(
            preds=preds,
            target=target,
            metric_module=BinaryConfusionMatrix,
            metric_functional=binary_confusion_matrix,
            metric_args={"threshold": THRESHOLD},
            dtype=dtype,
        )


def _sklearn_confusion_matrix_multiclass(preds, target, normalize=None, ignore_index=None):
    preds = preds.numpy()
    target = target.numpy()
    if np.issubdtype(preds.dtype, np.floating):
        preds = np.argmax(preds, axis=1)
    preds = preds.flatten()
    target = target.flatten()
    target, preds = remove_ignore_index(target, preds, ignore_index)
    return sk_confusion_matrix(y_true=target, y_pred=preds, normalize=normalize, labels=list(range(NUM_CLASSES)))


@pytest.mark.parametrize("input", _multiclass_cases)
class TestMulticlassConfusionMatrix(MetricTester):
    """Test class for `MultiClassConfusionMatrix` metric."""

    @pytest.mark.parametrize("normalize", ["true", "pred", "all", None])
    @pytest.mark.parametrize("ignore_index", [None, -1, 0])
    @pytest.mark.parametrize("ddp", [True, False])
    def test_multiclass_confusion_matrix(self, input, ddp, normalize, ignore_index):
        """Test class implementation of metric."""
        preds, target = input
        if ignore_index is not None:
            target = inject_ignore_index(target, ignore_index)
        self.run_class_metric_test(
            ddp=ddp,
            preds=preds,
            target=target,
            metric_class=MulticlassConfusionMatrix,
            reference_metric=partial(
                _sklearn_confusion_matrix_multiclass,
                normalize=normalize,
                ignore_index=ignore_index,
            ),
            metric_args={
                "num_classes": NUM_CLASSES,
                "normalize": normalize,
                "ignore_index": ignore_index,
            },
        )

    @pytest.mark.parametrize("normalize", ["true", "pred", "all", None])
    @pytest.mark.parametrize("ignore_index", [None, -1, 0])
    def test_multiclass_confusion_matrix_functional(self, input, normalize, ignore_index):
        """Test functional implementation of metric."""
        preds, target = input
        if ignore_index is not None:
            target = inject_ignore_index(target, ignore_index)
        self.run_functional_metric_test(
            preds=preds,
            target=target,
            metric_functional=multiclass_confusion_matrix,
            reference_metric=partial(
                _sklearn_confusion_matrix_multiclass,
                normalize=normalize,
                ignore_index=ignore_index,
            ),
            metric_args={
                "num_classes": NUM_CLASSES,
                "normalize": normalize,
                "ignore_index": ignore_index,
            },
        )

    def test_multiclass_confusion_matrix_differentiability(self, input):
        """Test the differentiability of the metric, according to its `is_differentiable` attribute."""
        preds, target = input
        self.run_differentiability_test(
            preds=preds,
            target=target,
            metric_module=MulticlassConfusionMatrix,
            metric_functional=multiclass_confusion_matrix,
            metric_args={"num_classes": NUM_CLASSES},
        )

    @pytest.mark.parametrize("dtype", [torch.half, torch.double])
    def test_multiclass_confusion_matrix_dtype_cpu(self, input, dtype):
        """Test dtype support of the metric on CPU."""
        preds, target = input

        self.run_precision_test_cpu(
            preds=preds,
            target=target,
            metric_module=MulticlassConfusionMatrix,
            metric_functional=multiclass_confusion_matrix,
            metric_args={"num_classes": NUM_CLASSES},
            dtype=dtype,
        )

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="test requires cuda")
    @pytest.mark.parametrize("dtype", [torch.half, torch.double])
    def test_multiclass_confusion_matrix_dtype_gpu(self, input, dtype):
        """Test dtype support of the metric on GPU."""
        preds, target = input
        self.run_precision_test_gpu(
            preds=preds,
            target=target,
            metric_module=MulticlassConfusionMatrix,
            metric_functional=multiclass_confusion_matrix,
            metric_args={"num_classes": NUM_CLASSES},
            dtype=dtype,
        )


def test_multiclass_overflow():
    """Test that multiclass computations does not overflow even on byte input."""
    preds = torch.randint(20, (100,)).byte()
    target = torch.randint(20, (100,)).byte()

    m = MulticlassConfusionMatrix(num_classes=20)
    res = m(preds, target)

    compare = sk_confusion_matrix(target, preds)
    assert torch.allclose(res, torch.tensor(compare))


def _sklearn_confusion_matrix_multilabel(preds, target, normalize=None, ignore_index=None):
    preds = preds.numpy()
    target = target.numpy()
    if np.issubdtype(preds.dtype, np.floating):
        if not ((preds > 0) & (preds < 1)).all():
            preds = sigmoid(preds)
        preds = (preds >= THRESHOLD).astype(np.uint8)
    preds = np.moveaxis(preds, 1, -1).reshape((-1, preds.shape[1]))
    target = np.moveaxis(target, 1, -1).reshape((-1, target.shape[1]))
    confmat = []
    for i in range(preds.shape[1]):
        pred, true = preds[:, i], target[:, i]
        true, pred = remove_ignore_index(true, pred, ignore_index)
        confmat.append(sk_confusion_matrix(true, pred, normalize=normalize, labels=[0, 1]))
    return np.stack(confmat, axis=0)


@pytest.mark.parametrize("input", _multilabel_cases)
class TestMultilabelConfusionMatrix(MetricTester):
    """Test class for `MultilabelConfusionMatrix` metric."""

    @pytest.mark.parametrize("normalize", ["true", "pred", "all", None])
    @pytest.mark.parametrize("ignore_index", [None, -1, 0])
    @pytest.mark.parametrize("ddp", [True, False])
    def test_multilabel_confusion_matrix(self, input, ddp, normalize, ignore_index):
        """Test class implementation of metric."""
        preds, target = input
        if ignore_index is not None:
            target = inject_ignore_index(target, ignore_index)
        self.run_class_metric_test(
            ddp=ddp,
            preds=preds,
            target=target,
            metric_class=MultilabelConfusionMatrix,
            reference_metric=partial(
                _sklearn_confusion_matrix_multilabel,
                normalize=normalize,
                ignore_index=ignore_index,
            ),
            metric_args={
                "num_labels": NUM_CLASSES,
                "normalize": normalize,
                "ignore_index": ignore_index,
            },
        )

    @pytest.mark.parametrize("normalize", ["true", "pred", "all", None])
    @pytest.mark.parametrize("ignore_index", [None, -1, 0])
    def test_multilabel_confusion_matrix_functional(self, input, normalize, ignore_index):
        """Test functional implementation of metric."""
        preds, target = input
        if ignore_index is not None:
            target = inject_ignore_index(target, ignore_index)
        self.run_functional_metric_test(
            preds=preds,
            target=target,
            metric_functional=multilabel_confusion_matrix,
            reference_metric=partial(
                _sklearn_confusion_matrix_multilabel,
                normalize=normalize,
                ignore_index=ignore_index,
            ),
            metric_args={
                "num_labels": NUM_CLASSES,
                "normalize": normalize,
                "ignore_index": ignore_index,
            },
        )

    def test_multilabel_confusion_matrix_differentiability(self, input):
        """Test the differentiability of the metric, according to its `is_differentiable` attribute."""
        preds, target = input
        self.run_differentiability_test(
            preds=preds,
            target=target,
            metric_module=MultilabelConfusionMatrix,
            metric_functional=multilabel_confusion_matrix,
            metric_args={"num_labels": NUM_CLASSES, "threshold": THRESHOLD},
        )

    @pytest.mark.parametrize("dtype", [torch.half, torch.double])
    def test_multilabel_confusion_matrix_dtype_cpu(self, input, dtype):
        """Test dtype support of the metric on CPU."""
        preds, target = input

        if (preds < 0).any() and dtype == torch.half:
            pytest.xfail(reason="torch.sigmoid in metric does not support cpu + half precision")
        self.run_precision_test_cpu(
            preds=preds,
            target=target,
            metric_module=MultilabelConfusionMatrix,
            metric_functional=multilabel_confusion_matrix,
            metric_args={"num_labels": NUM_CLASSES, "threshold": THRESHOLD},
            dtype=dtype,
        )

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="test requires cuda")
    @pytest.mark.parametrize("dtype", [torch.half, torch.double])
    def test_multilabel_confusion_matrix_dtype_gpu(self, input, dtype):
        """Test dtype support of the metric on GPU."""
        preds, target = input
        self.run_precision_test_gpu(
            preds=preds,
            target=target,
            metric_module=MultilabelConfusionMatrix,
            metric_functional=multilabel_confusion_matrix,
            metric_args={"num_labels": NUM_CLASSES, "threshold": THRESHOLD},
            dtype=dtype,
        )


def test_warning_on_nan():
    """Test that a warning is given if division by zero happens during normalization of confusion matrix."""
    preds = torch.randint(3, size=(20,))
    target = torch.randint(3, size=(20,))

    with pytest.warns(
        UserWarning,
        match=".* NaN values found in confusion matrix have been replaced with zeros.",
    ):
        multiclass_confusion_matrix(preds, target, num_classes=5, normalize="true")
