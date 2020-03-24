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


class RSEICHAPlot(Plot):
    def plot(self, *args, **kwargs):
        dt = datetime.timedelta(days=1)
        m = self.model
        idx = [m.start_date + t * dt for t in self.data.index]

        def df(which):
            df = m[which]
            # df.index = idx
            return df

        i = df('infected')
        f = df('fatalities')
        h = df('hospitalized')
        c = df('critical')

        f.plot(label='Fatalities')
        (f + c).plot(label='Critical')
        (f + c + h).plot(label='Hospitalized')
        (f + c + i).plot(label='Infected')
        plt.legend()