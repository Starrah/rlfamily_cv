from abc import abstractmethod
from functools import wraps
import numpy as np
import pdb

from rl.tools.function_approximators import FunctionApproximator
from rl.tools.utils import minibatch_utils


def predict_in_batches(fun):
    """ for wrapping a predit method of FunctionApproximator objects """
    @wraps(fun)
    def wrapper(self, x):
        return minibatch_utils.apply_in_batches(lambda _x: fun(self, _x),
                                                x, self._batch_size_for_prediction, [self.y_dim])
    return wrapper


class SupervisedLearner(FunctionApproximator):
    """
    FunctionApproximator trained in a supervised learning manner on aggregated
    data.

    Its predict method can be decorated with predict_in_batches decorator for
    considering memory constraint.
    """

    def __init__(self, x_dim, y_dim, name='SupervisedLearner', seed=None,
                 use_aggregation=False, max_n_samples=None,
                 max_n_update_samples=None,
                 batch_size_for_prediction=2048):

        super().__init__(x_dim, y_dim, name=name, seed=seed)
        # for prediction considering memory limit
        self._batch_size_for_prediction = batch_size_for_prediction
        # for data aggregation
        self._use_aggregation = use_aggregation
        self._max_n_samples = max_n_samples  # None, for using all samples
        self._agg_data = {'x': None, 'y': None, 'w': None}
        # Store the number of samples seen in each update.
        # Its max length is self._max_n_update_samples.
        self._n_samples_per_update = np.array([], dtype=int)
        self._max_n_update_samples = max_n_update_samples

    def update(self, x, y, w=1.0, *args, **kwargs):
        """ Update the function approximator through supervised learning, where
        x, y, and w are inputs, outputs, and the weight on each datum.  """
        w = np.ones(x.shape[0]) * w if type(w) is not np.ndarray else w
        assert x.shape[0] == y.shape[0] == w.shape[0]
        # update self._agg_data
        self._update_agg_data('x', x)
        self._update_agg_data('y', y)
        self._update_agg_data('w', w)
        # user-define optimization routine
        self._update_func_approx(x, y, w, *args, **kwargs)  # user-defined

    def _update_agg_data(self, name, new):
        # aggregate data up to max_n_samples or max_n_update_samples (i.e. only use the samples from
        # last several updates)
        if self._use_aggregation:
            # First aggregate anyway.
            if self._agg_data[name] is None:
                self._agg_data[name] = np.copy(new)  # copy for safety
            else:
                self._agg_data[name] = np.concatenate([self._agg_data[name], new], axis=0)
            # Then reduce data if necessary.
            # BOTH max_n_samples and max_n_update_samples are considered.
            if self._max_n_samples is not None:   # save most recent max_n_samples
                self._agg_data[name] = self._agg_data[name][-self._max_n_samples:]
            if self._max_n_update_samples is not None:
                pdb.set_trace()
                idx = 0
                if len(self._n_samples_per_update) == self._max_n_update_samples:
                    idx = 1  # need to remove the first item
                self._n_samples_per_update = np.append(self._n_samples_per_update[idx:], len(new))
                self._agg_data[name] = self._agg_data[name][-np.sum(self._n_samples_per_update):]

        else:  # just record newest value
            self._agg_data[name] = np.copy(new)

    # Methods to be implemented
    @abstractmethod
    def _update_func_approx(self, x, y, w, *args, **kwargs):
        """ Update the function approximator based on the current data (x, y,
        w) or through self._agg_data which is up-to-date with (x, y, w). """
