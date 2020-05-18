import warnings

from invoke import task


@task
def compilemessages(ctx):
    ctx.run("pybabel compile -d covid/locale")


@task
def makemessages(ctx):
    ctx.run("pybabel extract -o covid/locale/messages.pot covid")
    ctx.run("pybabel update -i covid/locale/messages.pot -d covid/locale")


@task
def i18n(ctx):
    makemessages(ctx)
    compilemessages(ctx)


@task
def test(ctx):
    ctx.run("black --check .")
    ctx.run("pycodestyle")
    ctx.run("coverage run -m pytest")
    ctx.run("coverage report --show-missing")
