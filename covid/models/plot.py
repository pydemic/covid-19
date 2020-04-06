import datetime

import seaborn as sns
from matplotlib import pyplot as plt

from ..types import alias

MONTH = [None, "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
to_date = lambda d: f"{MONTH[d.month]}-{d.day}"


class Plot:
    data = alias("model.datasets")

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

        i = df("infectious")
        a = df("asymptomatic")
        f = df("fatalities")
        h = df("hospitalized")
        c = df("critical")

        im = i + self.model.rho * a
        f.plot(label="fatalities")
        im.plot(label="infectious")
        h.plot(label="hospitalized")
        (h + c).plot(label="critical")
        plt.legend()

    def healthcare_overflow(
        self,
        duration=None,
        t0=0,
        ymin=10,
        legend=True,
        log=True,
        ylabel="número de casos",
        xticks=True,
        title="Evolução do número de internações COVID-19",
    ):
        """
        Plot evolution of patients with healthcare capacity.
        """

        m = self.model

        tf = None if duration is None else t0 + duration
        h = m["hospitalized:total:dates"].iloc[t0:tf]
        c = m["critical:total:dates"].iloc[t0:tf]

        g = sns.lineplot(data=h, label="Enfermaria")
        c1 = g.get_lines()[-1].get_color()

        g = sns.lineplot(data=c, label="UTI")
        c2 = g.get_lines()[-1].get_color()

        plt.plot(h.index, [m.hospital_capacity] * len(h), "--", c=c1, lw=2)
        plt.plot(h.index, [m.icu_capacity] * len(h), "--", c=c2, lw=2)

        if not xticks:
            g.set_xticks([])
        else:
            g.set_xticks(c.index[::7])
            g.set_xticklabels(map(to_date, c.index[::7]), rotation=45)

        plt.title(title)
        if ylabel:
            plt.ylabel(ylabel)

        if log:
            plt.yscale("log")
        plt.ylim((ymin, plt.ylim()[1]))

        if legend:
            plt.legend()
