from invoke import task


@task
def i18n(ctx):
    ctx.run("pybabel extract -o covid/locale/messages.pot covid")
    ctx.run("pybabel update -i covid/locale/messages.pot -d covid/locale")
    ctx.run("pybabel compile -d covid/locale")
