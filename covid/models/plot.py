from matplotlib import pyplot as plt
import datetime

from ..types import alias


class Plot:
    data = alias('model.data')

    def __init__(self, model):
        self.model = model

    def __call__(self, *args, show=False, **kwargs):
        res = self.plot(*args, **kwargs)
        if show:
            plt.show()
        else:
            return res

    def plot(self, *args, **kwargs):
        return self.data[self.model.display_columns].plot()


class SEICHARPlot(Plot):
    def plot(self, *args, **kwargs):
        dt = datetime.timedelta(days=1)
        m = self.model
        idx = [m.start_date + t * dt for t in self.data.index]

        def df(which):
            df = m[which]
            # df.index = idx
            return df

        i = df('infected')
        a = df('asymptomatic')
        f = df('fatalities')
        h = df('hospitalized')
        c = df('critical')

        im = i + self.model.rho * a
        f.plot(label='Fatalities')
        im.plot(label='Infected')
        h.plot(label='Hospitalized')
        (h + c).plot(label='Critical')
        plt.legend()