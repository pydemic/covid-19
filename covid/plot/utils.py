import humanize
import matplotlib.pyplot as plt


def adj_dates(angle=0, pretty=False):
    """
    Adjust dates in the horizontal label of a matplotlib plot.
    """

    xs, _ = plt.xticks()
    labels = None
    if pretty:
        pretty = (lambda x: humanize.naturaldate(x).title()) if pretty is True else pretty
        labels = [pretty(date.fromordinal(x)) for x in xs]
    plt.xticks(xs, labels, rotation=angle)
