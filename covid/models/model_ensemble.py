import numpy as np
import pandas as pd

from .model import Model


class ModelEnsemble(Model):
    """
    Run multiple simulations of the same model with different and randomly
    chosen parameters.
    """

    ensemble_size = 5

    def __init__(self, cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.distributions = {k: v for k, v in kwargs.items() if hasattr(k, "rvs")}
        self.factory_method = cls
        self.params = pd.DataFrame({k: v.rvs(self.ensemble_size) for k, v in self.distributions})

        kw = {k: v for k, v in kwargs.items() if k not in self.distributions}
        self.models = [cls(*args, **kw, **row.to_dict()) for row in self.params]

    def run(self, *args, **kwargs) -> "Model":
        for model in self.models:
            model.run(*args, **kwargs)
        return self

    def mean(self, col):
        """Return a dataframe with the mean value computed over all samples
        for the given column."""

        values = [m[col] for m in self.models]
        ndim = np.ndim(values[0])

        if ndim == 0:
            return np.mean(values)
        else:
            return np.array(values).mean(ndim)

    def std(self, col):
        pass

    def ci(self, col):
        pass

    def stats(self, col):
        pass


if __name__ == "__main__":
    m = ModelEnsemble.main()
